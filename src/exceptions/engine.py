import hashlib
import pandas as pd

STATUSES = ["Open", "Investigating", "Resolved", "Accepted"]
ACTIONS = {
    "STOCKOUT_RISK": "Expedite purchase receipts or schedule production; rebalance from surplus facilities.",
    "EXCESS_INVENTORY": "Reduce replenishment and production; transfer surplus to demand locations.",
    "SUPPLIER_DELAY": "Confirm supplier recovery date and qualify an alternate source.",
    "SHIPMENT_DELAY": "Contact carrier for recovery; review route capacity and notify customer through normal operations.",
    "ORDER_BACKLOG": "Prioritize overdue orders and reconcile inventory with production capacity.",
    "LOW_SUPPLIER_OTIF": "Review delivery and quantity failures with supplier; consider alternate allocations.",
    "HIGH_DEMAND_VOLATILITY": "Review seasonal drivers and safety stock; monitor forecast error.",
    "PRODUCTION_SHORTFALL": "Investigate downtime, material shortages and schedule adherence.",
}


def exception_id(kind, reference):
    return "EX-"+hashlib.sha256(f"{kind}:{reference}".encode()).hexdigest()[:16]


def generate_exceptions(t: dict, a: dict, projection: pd.DataFrame, cfg: dict, previous=None):
    as_of = t["fact_inventory"].snapshot_date.max()
    rows = []
    previous = previous or {}
    def add(kind, reference, metric, actual, threshold, expected, severity="Medium", facility=None, product=None, supplier=None):
        eid = exception_id(kind, reference)
        rows.append({"exception_id": eid, "type": kind, "severity": severity, "facility_id": facility, "product_id": product, "supplier_id": supplier, "reference": str(reference), "detected_date": str(as_of.date()), "metric": metric, "threshold": float(threshold), "actual_value": float(actual), "expected_value": float(expected), "status": previous.get(eid, "Open"), "recommended_action": ACTIONS[kind]})
    for (pid, fid), group in projection.groupby(["product_id", "facility_id"]):
        risk = group[group.stockout_flag == 1].sort_values("horizon")
        if not risk.empty:
            r = risk.iloc[0]
            add("STOCKOUT_RISK", f"P{pid}-F{fid}", "projected_ending_inventory", r.projected_ending_inventory, cfg["stockout_threshold"], cfg["stockout_threshold"], "Critical" if r.horizon == 1 else "High", fid, pid)
        excess = group[group.excess_inventory_flag == 1].sort_values("horizon")
        if not excess.empty:
            r = excess.iloc[0]
            # Quantity-based comparison avoids undefined days when demand is zero.
            target = r.forecast_demand/pd.Timestamp(r.forecast_date).days_in_month*cfg["excess_days"]
            add("EXCESS_INVENTORY", f"P{pid}-F{fid}", "projected_ending_inventory", r.projected_ending_inventory, target, target, "Low", fid, pid)
    for r in a["agg_supplier"].itertuples():
        if pd.notna(r.supplier_otif) and r.supplier_otif < cfg["low_supplier_otif"]:
            add("LOW_SUPPLIER_OTIF", f"S{r.supplier_id}", "supplier_otif", r.supplier_otif, cfg["low_supplier_otif"], 1, "High", supplier=r.supplier_id)
    recent = as_of.replace(day=1)
    for r in t["fact_supplier_delivery"].itertuples():
        if r.delivery_date >= recent and r.delay_days > cfg["delay_days_threshold"]:
            add("SUPPLIER_DELAY", f"D{r.delivery_id}", "delay_days", r.delay_days, cfg["delay_days_threshold"], 0, "High" if r.delay_days > 7 else "Medium", r.facility_id, r.product_id, r.supplier_id)
    for r in t["fact_purchase_order"].itertuples():
        delay = (as_of-r.expected_date).days
        if r.status == "Open" and delay > cfg["delay_days_threshold"]:
            add("SUPPLIER_DELAY", f"PO{r.po_id}", "overdue_days", delay, cfg["delay_days_threshold"], 0, "High", r.facility_id, r.product_id, r.supplier_id)
    for r in t["fact_shipment"].itertuples():
        if r.actual_delivery_date >= recent and r.delay_days > cfg["delay_days_threshold"]:
            add("SHIPMENT_DELAY", f"SH{r.shipment_id}", "delay_days", r.delay_days, cfg["delay_days_threshold"], 0, "High" if r.delay_days > 7 else "Medium", r.facility_id, r.product_id)
    for r in t["fact_sales_order"].itertuples():
        if r.backlog_quantity > cfg["backlog_quantity_threshold"] and r.required_date < as_of:
            add("ORDER_BACKLOG", f"L{r.line_id}", "backlog_quantity", r.backlog_quantity, cfg["backlog_quantity_threshold"], 0, "Critical" if (as_of-r.required_date).days > 30 else "High", r.facility_id, r.product_id)
    monthly = a["agg_demand"].groupby(["product_id", "month"]).demand_quantity.sum().reset_index()
    for pid, group in monthly.groupby("product_id"):
        mean = group.demand_quantity.mean()
        cv = group.demand_quantity.std()/mean if mean else 0
        if cv > cfg["volatility_threshold"]:
            add("HIGH_DEMAND_VOLATILITY", f"P{pid}", "demand_coefficient_of_variation", cv, cfg["volatility_threshold"], cfg["volatility_threshold"], "Medium", product=int(pid))
    for r in t["fact_production"].itertuples():
        attainment = r.produced_quantity/r.planned_quantity if r.planned_quantity else 1
        if r.production_date == as_of and attainment < cfg["production_shortfall_threshold"]:
            add("PRODUCTION_SHORTFALL", f"PR{r.production_id}", "production_attainment", attainment, cfg["production_shortfall_threshold"], 1, "High" if attainment < .8 else "Medium", r.facility_id, r.product_id)
    columns = ["exception_id", "type", "severity", "facility_id", "product_id", "supplier_id", "reference", "detected_date", "metric", "threshold", "actual_value", "expected_value", "status", "recommended_action"]
    return pd.DataFrame(rows, columns=columns)
