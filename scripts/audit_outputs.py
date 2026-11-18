"""Independent SQL/output checks on the full executed dataset; exits on failures."""
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import compileall
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from src.config import root_path
from src.exceptions.engine import ACTIONS


def audit(root=None):
    root = root or root_path()
    report = json.loads((root/"outputs/reports/run_summary.json").read_text())
    checks = []
    def check(name, passed, detail=None):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
    with closing(sqlite3.connect(root/"database/control_tower.sqlite")) as db:
        db.row_factory = sqlite3.Row
        scalar = lambda sql: db.execute(sql).fetchone()[0]
        check("foreign keys", len(db.execute("PRAGMA foreign_key_check").fetchall()) == 0)
        check("database integrity", scalar("PRAGMA integrity_check") == "ok")
        expected_min = {"dim_customer": 500, "dim_product": 200, "dim_supplier": 100, "dim_facility": 5, "dim_carrier": 15, "fact_sales_order": 20000, "fact_production": 10000, "fact_inventory": 20000, "fact_purchase_order": 5000, "fact_supplier_delivery": 5000, "fact_shipment": 10000}
        check("minimum entity counts", all(report["record_counts"][k] >= v for k, v in expected_min.items()), report["record_counts"])
        check("minimum distinct orders", scalar("SELECT COUNT(DISTINCT order_id) FROM fact_sales_order") >= 10000)
        check("30 monthly history periods", scalar("SELECT COUNT(DISTINCT substr(snapshot_date,1,7)) FROM fact_inventory") == 30)
        check("demand aggregation", scalar("SELECT SUM(ordered_quantity) FROM fact_sales_order") == scalar("SELECT SUM(demand_quantity) FROM agg_demand"))
        check("inventory balance", scalar("SELECT COUNT(*) FROM fact_inventory WHERE on_hand_quantity!=opening_quantity+production_quantity+receipt_quantity-consumed_quantity") == 0)
        for qty, source, date_col in [("production_quantity", "fact_production", "production_date"), ("receipt_quantity", "fact_supplier_delivery", "delivery_date"), ("consumed_quantity", "fact_sales_order", "order_date")]:
            source_qty = {"production_quantity": "produced_quantity", "receipt_quantity": "delivered_quantity", "consumed_quantity": "fulfilled_quantity"}[qty]
            invalid = scalar(f"SELECT COUNT(*) FROM fact_inventory i LEFT JOIN (SELECT product_id,facility_id,substr({date_col},1,7) m,SUM({source_qty}) q FROM {source} GROUP BY 1,2,3) x ON i.product_id=x.product_id AND i.facility_id=x.facility_id AND substr(i.snapshot_date,1,7)=x.m WHERE i.{qty}!=COALESCE(x.q,0)")
            check(f"{qty} ledger reconciles", invalid == 0)
        current = scalar("SELECT SUM(on_hand_quantity) FROM fact_inventory WHERE snapshot_date=(SELECT MAX(snapshot_date) FROM fact_inventory)")
        check("current inventory snapshot", current == report["kpis"]["inventory_quantity"])
        orders = scalar("SELECT COUNT(DISTINCT order_id) FROM fact_sales_order")
        fulfilled = scalar("SELECT COUNT(*) FROM (SELECT order_id FROM fact_sales_order GROUP BY order_id HAVING SUM(fulfilled_quantity)>=SUM(ordered_quantity))")
        check("order fulfillment denominator", np.isclose(fulfilled/orders, report["kpis"]["fulfillment_rate"]))
        for table, kpi, date_col, promised in [("fact_shipment", "logistics_otif", "actual_delivery_date", "promised_date"), ("fact_supplier_delivery", "supplier_otif", "delivery_date", "expected_date")]:
            actual = scalar(f"SELECT AVG(CASE WHEN {date_col}<={promised} AND delivered_quantity>=ordered_quantity THEN 1.0 ELSE 0 END) FROM {table}")
            check(f"{kpi} independently calculated", np.isclose(actual, report["kpis"][kpi]), actual)
        cogs = scalar("SELECT SUM(fulfilled_quantity*standard_cost) FROM fact_sales_order JOIN dim_product USING(product_id)")
        avg_inv = scalar("SELECT AVG(v) FROM (SELECT snapshot_date,SUM(on_hand_quantity*standard_cost) v FROM fact_inventory JOIN dim_product USING(product_id) GROUP BY snapshot_date)")
        check("value-based turnover", np.isclose(cogs/avg_inv, report["kpis"]["inventory_turnover"]))
        check("all eight exceptions", {r[0] for r in db.execute("SELECT DISTINCT type FROM supply_chain_exception")} == set(ACTIONS))
        check("exception counts reconcile", scalar("SELECT COUNT(*) FROM supply_chain_exception") == sum(report["exception_counts"].values()))
        check("positive predictions", scalar("SELECT COUNT(*) FROM forecast_demand WHERE prediction<0 OR actual IS NOT NULL") == 0)
        check("holdout chronology", scalar("SELECT MAX(forecast_date) FROM forecast_validation") < scalar("SELECT MIN(forecast_date) FROM forecast_test"))
        check("holdout actuals reconcile", scalar("SELECT COUNT(*) FROM forecast_test f JOIN (SELECT product_id,month,SUM(demand_quantity) q FROM agg_demand GROUP BY 1,2) a ON f.product_id=a.product_id AND f.forecast_date=a.month WHERE f.actual!=a.q") == 0)
        check("forecast allocation reconciles", scalar("SELECT COUNT(*) FROM forecast_demand f JOIN (SELECT product_id,horizon,SUM(forecast_demand) q FROM projected_inventory GROUP BY 1,2) p USING(product_id,horizon) WHERE ABS(f.prediction-p.q)>0.000001") == 0)
        check("projected inventory balance", scalar("SELECT COUNT(*) FROM projected_inventory WHERE ABS(projected_ending_inventory-opening_inventory-expected_receipts+forecast_demand)>0.000001") == 0)
        check("stockout signs", scalar("SELECT COUNT(*) FROM projected_inventory WHERE stockout_flag!=(projected_ending_inventory<=0)") == 0)
        check("no broken shipment lineage", scalar("SELECT COUNT(*) FROM fact_shipment sh JOIN fact_sales_order so USING(line_id) WHERE sh.product_id!=so.product_id OR sh.order_id!=so.order_id OR sh.delivered_quantity!=so.fulfilled_quantity") == 0)
        # Test simulated systematic behaviors without claiming real-world causality.
        supplier_behavior = pd.read_sql_query("SELECT supplier_tier,AVG(supplier_otif) otif FROM agg_supplier GROUP BY supplier_tier", db).set_index("supplier_tier").otif.to_dict()
        check("watch suppliers perform worse", supplier_behavior["Watch"] < supplier_behavior["Preferred"], supplier_behavior)
        carriers = pd.read_sql_query("SELECT CASE WHEN carrier_id%5=0 THEN 'slow' ELSE 'regular' END type,AVG(delay_days) delay FROM fact_shipment GROUP BY 1", db).set_index("type").delay.to_dict()
        check("carrier delay behavior", carriers["slow"] > carriers["regular"], carriers)
        seasonal = pd.read_sql_query("SELECT month,SUM(demand_quantity) q FROM agg_demand JOIN dim_product USING(product_id) WHERE seasonal=1 GROUP BY month ORDER BY month", db)
        seasonal_signal = np.sin(2*np.pi*(pd.to_datetime(seasonal.month).dt.month.to_numpy()-1)/12)
        corr = float(np.corrcoef(seasonal.q, seasonal_signal)[0, 1])
        check("seasonal demand signal", corr > .5, corr)
    manifest = json.loads((root/"outputs/powerbi/manifest.json").read_text())
    for name, meta in manifest.items():
        file = root/"outputs/powerbi"/name
        frame = pd.read_csv(file)
        check(f"export {name}", len(frame) == meta["rows"] and list(frame.columns) == meta["columns"] and hashlib.sha256(file.read_bytes()).hexdigest() == meta["sha256"])
    check("six quarantined source defects", report["rejected_rows"] == 6)
    check("all pipeline layers exist", all(list((root/"data"/layer).glob("*.csv")) for layer in ["staging", "processed", "curated"]))
    # Source-only hygiene scan: external credentials are never printed or opened.
    bad = []
    for directory in [root/"src", root/"scripts", root/"tests", root/"config"]:
        for file in directory.rglob("*"):
            if file.suffix not in [".py", ".json"]:
                continue
            text = file.read_text(encoding="utf-8")
            if re.search(r"[A-Z]:[\\/](?:Users|projects)|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}", text):
                bad.append(str(file.relative_to(root)))
    check("no machine paths or recognizable secrets in source", not bad, bad)
    check("no fabricated PBIX", not list(root.rglob("*.pbix")))
    compiled = all(compileall.compile_dir(root/folder, quiet=1) for folder in ("src", "scripts", "tests"))
    check("Python compilation", compiled)
    dependencies = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True, check=False)
    check("dependency consistency", dependencies.returncode == 0, dependencies.stdout.strip())
    result = {"executed_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(), "passed": sum(x["passed"] for x in checks), "total": len(checks), "checks": checks}
    (root/"outputs/reports/output_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    failures = [x for x in checks if not x["passed"]]
    if failures:
        raise AssertionError(json.dumps(failures, indent=2))
    print(f"Output audit: {result['passed']}/{result['total']} checks passed")
    return result


if __name__ == "__main__":
    audit()
