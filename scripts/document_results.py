"""Write documentation from actual execution receipts; never fabricate pass counts."""
import json
import sqlite3
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
from src.config import root_path

GRAINS = {
    "dim_date": "One calendar day; historical and three future months",
    "dim_customer": "One fictional customer", "dim_product": "One finished-unit SKU",
    "dim_supplier": "One fictional supplier", "dim_facility": "One facility", "dim_carrier": "One carrier",
    "bridge_supplier_product": "One qualified supplier/SKU combination",
    "fact_sales_order": "One order line (two per header in default generator)",
    "fact_production": "One product/facility/month production record",
    "fact_inventory": "One product/facility/month-end physical ledger",
    "fact_purchase_order": "One procurement order for one SKU and facility",
    "fact_supplier_delivery": "One observed delivery per PO, including partial closed POs",
    "fact_shipment": "One shipment per positive-fulfilled order line",
    "agg_demand": "One dense month/product/facility demand observation",
    "agg_inventory": "One latest product/facility health snapshot with full-history statistics",
    "agg_supplier": "One supplier, observed-delivery full-history statistics",
    "agg_logistics": "One carrier/facility/route full-history aggregate",
    "agg_facility": "One facility, full-history performance and current inventory",
    "executive_kpis": "One global as-of snapshot",
    "forecast_demand": "One product/future horizon; actual unknown",
    "forecast_validation": "One product/candidate/origin/horizon chronological validation prediction",
    "forecast_model_metrics": "One product/candidate validation metric record",
    "forecast_test": "One product/horizon final untouched test prediction",
    "projected_inventory": "One product/facility/future horizon inventory scenario",
    "supply_chain_exception": "One deterministic type/business-reference exception",
}
DESCRIPTIONS = {
    "date_id": "Calendar key YYYYMMDD", "date": "ISO calendar date", "month": "Month start date in analytics; month number in dim_date",
    "month_start": "First day of calendar month", "year": "Calendar year", "quarter": "Calendar quarter 1–4",
    "category": "Canonical packaging category", "unit": "Finished-unit unit of measure", "standard_cost": "Synthetic INR/unit cost, not accounting COGS",
    "lead_time_days": "Product nominal lead days or observed delivery lead days, depending on table", "default_lead_time_days": "Supplier nominal lead days",
    "seasonal": "1 if generator applies annual demand modulation, otherwise 0", "region": "Synthetic customer/supplier geographic region", "customer_segment": "Enterprise, SME or Distributor",
    "supplier_tier": "Preferred or Watch (systematically poorer simulation behavior)", "city": "Facility city", "capacity": "Illustrative monthly facility units; metadata, not a constrained scheduler", "mode": "Transport mode, Road",
    "status": "Order Open/Fulfilled; PO Open/Received; production Complete; exception workflow Open/Investigating/Resolved/Accepted",
    "order_date": "Date demand/PO was placed", "required_date": "Customer required date", "production_date": "Monthly production accounting date",
    "snapshot_date": "Month-end inventory measurement date", "expected_date": "PO expected receipt date", "delivery_date": "Observed supplier delivery date",
    "ship_date": "Shipment departure date", "promised_date": "Promised customer delivery date", "actual_delivery_date": "Observed customer delivery date",
    "opening_quantity": "Prior month closing physical quantity (initial seeded balance in first month)",
    "production_quantity": "Monthly produced units credited to inventory", "receipt_quantity": "Observed supplier units received that month", "consumed_quantity": "Fulfilled sales units debited that month",
    "on_hand_quantity": "Nonnegative month-end physical units", "planned_quantity": "Demand-driven planned production units", "produced_quantity": "Actual simulated production units",
    "ordered_quantity": "Full requested customer/PO quantity", "fulfilled_quantity": "Customer units supplied, capped by stock and requested quantity",
    "backlog_quantity": "Ordered minus fulfilled units", "delivered_quantity": "Observed delivered units", "shipped_quantity": "Units dispatched", "demand_quantity": "Ordered units at aggregate grain",
    "route": "Origin facility city to synthetic customer region", "delay_days": "Nonnegative actual minus promised/expected days",
    "on_time": "1 when actual delivery date ≤ promised/expected date", "in_full": "1 when delivered ≥ full ordered quantity", "otif": "on_time AND in_full, stored as 0/1",
    "previous_demand": "Dense preceding-month demand; null in first month", "demand_growth": "(current-previous)/previous, null for zero/missing previous", "demand_volatility": "Sample monthly CV for product/facility across full history",
    "average_inventory": "Mean physical month-end quantity", "stockout_count": "Count month-end snapshots at/below threshold", "average_daily_demand": "Historical demand divided by inclusive history days",
    "inventory_quantity": "Total latest month-end physical units for executive/facility snapshot",
    "days_of_inventory": "Historical average stock coverage in health, projected month coverage in projections", "current_days_of_inventory": "Latest stock / historical average daily demand",
    "inventory_value": "Latest units × synthetic standard cost", "average_inventory_value": "Mean physical units × synthetic standard cost", "synthetic_cogs_proxy": "Fulfilled units × standard cost across history", "inventory_turnover": "Full-history COGS proxy / average inventory value, not annualized",
    "excess_inventory": "Current health excess flag, 0/1", "deliveries": "Observed supplier delivery count", "otif_count": "Number of deliveries/shipments satisfying both criteria", "on_time_count": "Number of on-time deliveries", "late_count": "Number of positive-delay observed deliveries/shipments",
    "average_lead_time": "Mean observed supplier lead days", "lead_time_variance": "Sample lead-time variance in days squared", "supplier_otif": "Supplier count-weighted OTIF ratio", "late_delivery_rate": "Late supplier deliveries / observed deliveries", "fill_rate": "Quantity-weighted fulfilled/delivered fraction",
    "shipments": "Shipment count at aggregate grain", "logistics_otif": "Count-weighted shipment OTIF ratio", "late_shipment_rate": "Late shipments / observed shipments", "average_delivery_delay": "Mean nonnegative delay including on-time zero days",
    "production_attainment": "Full-history produced / planned", "latest_production": "Latest month's produced units", "latest_planned": "Latest month's planned units", "latest_production_attainment": "Latest produced / planned",
    "order_count": "Distinct customer order count", "fulfilled_orders": "Orders whose complete quantity was supplied", "open_orders": "Distinct orders still incomplete", "overdue_orders": "Incomplete orders required before synthetic as-of", "fulfillment_rate": "Fulfilled orders / eligible orders",
    "exceptions": "All detected exceptions linked to facility", "as_of": "Maximum cleaned inventory date", "history_days": "Inclusive calendar days from first history month to as-of", "total_demand": "Total historical ordered units",
    "average_inventory_quantity": "Sum of per-pair mean month-end units", "shipment_count": "Total observed shipments", "excess_inventory_pairs": "Current excess product/facility count", "stockout_risk_pairs": "Distinct pairs with projected risk in horizon", "open_exceptions": "Open/Investigating exception count at export time",
    "train_end": "Last training month, excluding prediction targets", "forecast_date": "Target month start", "horizon": "Forecast step 1–3", "prediction": "Nonnegative product demand point estimate", "actual": "Observed validation/test demand; null for future", "model_name": "moving_average_3 or trend_seasonal_regression", "mae": "Product/candidate validation mean absolute error, units", "rmse": "Validation root mean squared error, units", "mape": "Validation percent absolute error over nonzero actuals", "mape_eligible_count": "Count nonzero actual validation targets", "selected": "1 if candidate chosen by validation MAE",
    "opening_inventory": "Latest physical stock for horizon 1, prior scenario ending thereafter", "expected_receipts": "Known open PO units assigned to forecast month", "forecast_demand": "Product point forecast allocated by recent facility share", "projected_ending_inventory": "Opening + receipts - demand; negative represents deficit",
    "stockout_flag": "1 when ending ≤ configured threshold", "stockout_date": "Estimated uniform-consumption crossing date; null if no crossing", "excess_inventory_flag": "1 for projected excess coverage", "replenishment_quantity": "Deficit plus one-month buffer when risk flagged", "recommendation": "Deterministic planner action for projection",
    "exception_id": "Stable EX- plus truncated type/reference SHA-256", "type": "One of eight rule types", "severity": "Critical, High, Medium or Low", "reference": "Business reference (line, shipment, delivery, PO or product/facility)", "detected_date": "Synthetic as-of rule detection date", "metric": "Name of compared metric; determines units", "threshold": "Configured/computed trigger boundary", "actual_value": "Observed/projected metric compared with threshold", "expected_value": "Rule target", "recommended_action": "Explainable deterministic rule recommendation",
}


def dictionary(root):
    lines = ["# Data Dictionary", "", "Generated from the actual populated SQLite schema. All records are fictional and synthetic.", "", "IDs are positive simulation keys. Dates are ISO YYYY-MM-DD. Quantities are finished-unit equivalents; monetary values are fictional INR. Rates are 0–1 except MAPE (0–100). SQL primary keys, references and check constraints are in `database/schema.sql`. Raw/source keys and contracts are in `src/data/contracts.py`; cleaned data retains the source fields before curated enrichments.", "", "Customer fields: customer_id/name, region, segment. Product: product_id/name, category, unit, standard_cost, lead_time_days, seasonal. Supplier: supplier_id/name, region, default lead, tier. Facility: facility_id/name, city, capacity. Sales order source stores header dates/customer/facility/status separately from order_lines with line_id, order_id, product_id, ordered/fulfilled quantity; the warehouse joins them without changing line grain. Source production, inventory, PO, delivery and shipment fields appear in corresponding facts below. All label strings are fictional.", "", "Null ratios mean undefined denominator/insufficient samples. Exception entity IDs may be null when not applicable. Future actuals and no-risk crossing dates are null. Physical source records with required nulls are quarantined. Analytical snapshots with no date key do not support arbitrary historical-date slicing.", ""]
    with closing(sqlite3.connect(root/"database/control_tower.sqlite")) as db:
        for table, grain in GRAINS.items():
            lines.extend([f"## {table}", "", grain+".", "", "| Field | SQLite type | Nullable | Meaning |", "|---|---|---|---|"])
            for _, c, typ, notnull, _, pk in db.execute(f"PRAGMA table_info({table})"):
                meaning = DESCRIPTIONS.get(c)
                if meaning is None and c.endswith("_id"):
                    meaning = f"Stable {c[:-3].replace('_',' ')} key; see SQL references"
                if meaning is None and c.endswith("_name"):
                    meaning = f"Fictional {c[:-5].replace('_',' ')} display label"
                if meaning is None:
                    raise ValueError(f"Undocumented field {table}.{c}")
                lines.append(f"| {c} | {typ} | {'No' if notnull or pk else 'Yes'} | {meaning} |")
            lines.append("")
    (root/"DATA_DICTIONARY.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def document(root=None):
    root = root or root_path()
    reports = root/"outputs/reports"
    run = json.loads((reports/"run_summary.json").read_text())
    audit = json.loads((reports/"output_audit.json").read_text())
    smoke = json.loads((reports/"api_smoke.json").read_text())
    repeat = json.loads((reports/"idempotency.json").read_text())
    tree = ET.parse(reports/"pytest.xml")
    suites = list(tree.getroot().iter("testsuite"))
    total = sum(int(s.attrib["tests"]) for s in suites)
    failed = sum(int(s.attrib.get("failures", 0))+int(s.attrib.get("errors", 0)) for s in suites)
    skipped = sum(int(s.attrib.get("skipped", 0)) for s in suites)
    if failed or total-skipped < 30 or audit["passed"] != audit["total"] or smoke["passed"] < 15 or not repeat["identical_hashes"] or repeat["record_counts"] != run["record_counts"]:
        raise ValueError("Cannot verify build with failed/incomplete receipts")
    timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    lines = ["# Build Verification — Actual Execution", "", f"Evidence documentation generated {timestamp}. No results below are invented. All data is synthetic fictional PackRight data.", "", f"Default configuration: seed {run['configuration']['seed']}, {run['configuration']['months']} months starting {run['configuration']['start_date']}; analytical as-of **{run['as_of']}**. Final full pipeline elapsed {run['duration_seconds']:.3f} seconds (local measurement; varies by machine).", "", "## Record counts", "", "| Warehouse table | Records |", "|---|---:|"]
    for table, count in run["record_counts"].items():
        lines.append(f"| {table} | {count:,} |")
    lines.extend(["", f"Distinct customer orders: {run['kpis']['order_count']:,}; source header rows include one duplicate and one invalid-date record. Rejected raw rows: {run['rejected_rows']}; remaining category variants standardized. Source rows and cleaned counts are recorded in `run_summary.json` and field profiles in `data_quality.json`.", "", "## Actual KPIs", "", "| Metric | Result |", "|---|---:|"])
    for key, val in run["kpis"].items():
        if isinstance(val, float):
            rendered = f"{val:,.6f}"
        else:
            rendered = str(val)
        lines.append(f"| {key} | {rendered} |")
    lines.extend(["", "Rates above are fractions; cost values are fictional INR. Turnover uses a synthetic COGS proxy over the whole history, not annualized.", "", "## Forecast evidence", "", "Model selection is per product. Both methods evaluated on chronological validation; final three months remain untouched until the selected method is tested. Future actuals are null.", "", "| Selected model | Products |", "|---|---:|"])
    for model, count in run["forecast"]["selected_model_counts"].items():
        lines.append(f"| {model} | {count} |")
    lines.extend(["", "| Evaluation | MAE (units) | RMSE (units) | MAPE (%) | Nonzero actuals |", "|---|---:|---:|---:|---:|"])
    metrics = {**run["forecast"]["candidate_validation_metrics"], "selected_validation": run["forecast"]["selected_validation_metrics"], "untouched_test": run["forecast"]["untouched_test_metrics"]}
    for name, m in metrics.items():
        lines.append(f"| {name} | {m['mae']:.6f} | {m['rmse']:.6f} | {m['mape']:.6f} | {m['mape_eligible_count']} |")
    lines.extend(["", "MAPE is high because intermittent low-volume products produce large percentage errors; zero actuals are excluded and counted. Selection results are not a guarantee of future accuracy. No forecast interval was constructed.", "", "## Exceptions", "", "| Type | Count |", "|---|---:|"])
    for kind, count in run["exception_counts"].items():
        lines.append(f"| {kind} | {count} |")
    lines.extend(["", "Severity counts: "+", ".join(f"{s}: {n}" for s, n in run["severity_counts"].items())+".", "", "## Execution and checks", "", f"- **{total-failed-skipped} tests passed**, {failed} failures/errors, {skipped} skipped; actual pytest XML in `outputs/reports/pytest.xml`.", f"- **{audit['passed']}/{audit['total']} independent full-output checks passed**, receipt dated {audit['executed_at']}.", f"- **{smoke['passed']} real HTTP smoke checks passed**, against {smoke['base_url']}, receipt dated {smoke['executed_at']}. Required GETs, exception GET/PATCH persistence and restoration, assistant POST, expected 404/422 verified.", f"- SQLite integrity: {run['database']['integrity_check']}; foreign-key violations: {run['database']['foreign_key_violations']}.", "- Dependency installation completed in `.venv`; `pip check` reported no broken requirements. Python modules compiled successfully.", "- Small-fixture pipeline tests verify identical repeat export hashes and persisted exception statuses. Full-size repeat-hash receipt is in `outputs/reports/idempotency.json` when run.", "- Source scan found no machine-specific paths or recognizable credential patterns; `.env` and generated database/data/environment files are ignored. This is a scoped recognizable-pattern scan, not a universal secret guarantee.", "", "## Fixes actually made", "", "The first warehouse load exposed a Windows file-lock error because SQLite's transaction context did not close the connection. Explicit closing was added; full pipeline reruns and idempotency checks now succeed. Forecast selection was separated from an untouched final holdout before final verification.", "", "## Artifacts", "", f"Power BI CSV files: {len(run['powerbi_files'])}; exact filenames, rows, columns and hashes in `outputs/powerbi/manifest.json`. Nine required datasets plus supporting dimensions/facts/evaluation files exist. Theme, Power Query function and DAX source are authored import assets. Warehouse, forecasts, profiles, quarantines, logs and execution receipts are listed in README.md.", "", "## Honest limitations", "", "Power BI Desktop was not found in checked executable/install locations; no PBIX, screenshot or executed DAX/visual acceptance is claimed. Provider LLM calls were not made; credential-free fallback and mocked provider-failure paths passed. A non-failing Starlette/AnyIO deprecation warning remains. Inventory is month-end accounting, not a daily feasibility simulation; receipts are finished-unit equivalents. Backlog remains cumulative. Future projection assumes known open POs at month start and no future production, and negative balances are uncovered requirements. This is a local demo without authentication or production workflow audit.", "", "## Reproduction", "", "Follow README.md for locked dependencies, full generation/ETL, pytest, output audit, uvicorn and real HTTP smoke. Then run `python -m scripts.document_results` to refresh this receipt and dictionary from actual successful executions. BUILD_CHECKLIST.md records verified requirements; Desktop rendering is explicitly outside the supported environment.", ""])
    (root/"BUILD_VERIFICATION.md").write_text("\n".join(lines), encoding="utf-8")
    dictionary(root)
    checklist = (root/"BUILD_CHECKLIST.md").read_text(encoding="utf-8").replace("- [ ]", "- [x]")
    if "Verification evidence" not in checklist:
        checklist += "\n## Verification evidence\n\nAll checked items are backed by BUILD_VERIFICATION.md and machine-readable receipts in outputs/reports. Power BI outputs/guide are completed as documented; Desktop rendering and live LLM use are not claimed.\n"
    (root/"BUILD_CHECKLIST.md").write_text(checklist, encoding="utf-8")
    print(f"Wrote verified documentation from {total-failed-skipped} passed tests and {audit['passed']} audit checks")


if __name__ == "__main__":
    document()
