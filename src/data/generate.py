"""Demand-driven multi-source simulation with an auditable physical inventory ledger."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import prepare
from src.data.contracts import SOURCES

CATEGORIES = ["Fiber Packaging", "Metal Containers", "Polymer Packaging", "Industrial Drums", "Intermediate Bulk Containers"]
CITIES = ["Chennai", "Hyderabad", "Pune", "Mumbai", "Bengaluru"]


def generate(root: Path, cfg: dict) -> dict[str, pd.DataFrame]:
    prepare(root)
    rng = np.random.default_rng(cfg["seed"])
    months = pd.date_range(cfg["start_date"], periods=cfg["months"], freq="MS")
    as_of = months[-1] + pd.offsets.MonthEnd(0)
    npd = cfg["products"]
    tables = {}
    tables["customers"] = pd.DataFrame([
        [i, f"Customer {i:04d}", CITIES[(i-1) % 5], ["Enterprise", "SME", "Distributor"][i % 3]]
        for i in range(1, cfg["customers"]+1)], columns=["customer_id", "customer_name", "region", "customer_segment"])
    tables["products"] = pd.DataFrame([
        [i, f"PackRight SKU {i:03d}", CATEGORIES[(i-1) % 5], "unit", round(rng.uniform(80, 1500), 2), int(rng.integers(7, 25)), int(i % 4 == 0)]
        for i in range(1, npd+1)], columns=["product_id", "product_name", "category", "unit", "standard_cost", "lead_time_days", "seasonal"])
    tables["facilities"] = pd.DataFrame([[i+1, f"PackRight {city}", city, 20000] for i, city in enumerate(CITIES)], columns=["facility_id", "facility_name", "city", "capacity"])
    tables["suppliers"] = pd.DataFrame([
        [i, f"Supplier {i:03d}", CITIES[i % 5], 12+i % 12, "Watch" if i % 7 == 0 else "Preferred"]
        for i in range(1, cfg["suppliers"]+1)], columns=["supplier_id", "supplier_name", "region", "default_lead_time_days", "supplier_tier"])
    tables["carriers"] = pd.DataFrame([[i, f"Carrier {i:02d}", "Road"] for i in range(1, cfg["carriers"]+1)], columns=["carrier_id", "carrier_name", "mode"])
    mapping = []
    for p in range(1, npd+1):
        for j in range(2):
            mapping.append([len(mapping)+1, (p+j*13-1) % cfg["suppliers"]+1, p])
    tables["supplier_products"] = pd.DataFrame(mapping, columns=["supplier_product_id", "supplier_id", "product_id"])
    orders, lines = [], []
    weights = rng.lognormal(0, 0.7, npd)
    for m, month in enumerate(months):
        seasonal = np.array([1+0.55*np.sin(2*np.pi*(month.month-1)/12) if i % 4 == 0 else 1 for i in range(1, npd+1)])
        probability = weights*seasonal
        probability /= probability.sum()
        for _ in range(cfg["orders_per_month"]):
            oid = len(orders)+1
            date = month + pd.Timedelta(days=int(rng.integers(0, 20)))
            fid = int(rng.choice([1, 2, 3, 4, 5], p=[.24, .22, .20, .19, .15]))
            orders.append([oid, date, int(rng.integers(1, cfg["customers"]+1)), fid, date+pd.Timedelta(days=7), "Open"])
            for p in rng.choice(np.arange(1, npd+1), size=2, replace=False, p=probability):
                quantity = int(max(1, rng.lognormal(3.4, .45)*(1+m*.008)))
                lines.append([len(lines)+1, oid, int(p), quantity, 0])
    tables["sales_orders"] = pd.DataFrame(orders, columns=["order_id", "order_date", "customer_id", "facility_id", "required_date", "status"])
    sales = pd.DataFrame(lines, columns=["line_id", "order_id", "product_id", "ordered_quantity", "fulfilled_quantity"])
    joined = sales.merge(tables["sales_orders"], on="order_id")
    joined["month"] = joined.order_date.dt.to_period("M").dt.to_timestamp()
    demand = joined.groupby(["month", "facility_id", "product_id"]).ordered_quantity.sum()
    production = []
    for month in months:
        for fid in range(1, 6):
            for pid in range(1, npd+1):
                qty = float(demand.get((month, fid, pid), 0))
                # Five percent of SKUs overproduce; facility 5 has persistent shortfalls.
                target = qty*(1.50 if pid % 20 == 0 else (.57 if fid == 5 else .84))
                planned = int(round(target))
                produced = int(round(planned*rng.uniform(.82, 1.03)))
                production.append([len(production)+1, month+pd.offsets.MonthEnd(0), fid, pid, planned, produced, "Complete"])
    tables["production"] = pd.DataFrame(production, columns=["production_id", "production_date", "facility_id", "product_id", "planned_quantity", "produced_quantity", "status"])
    pos, deliveries = [], []
    supplier_lookup = tables["suppliers"].set_index("supplier_id")
    for month in months:
        for _ in range(cfg["purchase_orders_per_month"]):
            pid = int(rng.integers(1, npd+1))
            fid = int(rng.integers(1, 6))
            sid = (pid+int(rng.integers(0, 2))*13-1) % cfg["suppliers"]+1
            date = month+pd.Timedelta(days=int(rng.integers(0, 10)))
            lead = int(supplier_lookup.loc[sid, "default_lead_time_days"])
            expected = date+pd.Timedelta(days=lead)
            delay = int(rng.integers(5, 15) if sid % 7 == 0 else rng.choice([-2, -1, 0, 0, 0, 2, 4]))
            actual = expected+pd.Timedelta(days=delay)
            qty = int(max(10, demand.get((month, fid, pid), 0)*rng.uniform(.4, .9)))
            poid = len(pos)+1
            received = actual <= as_of
            pos.append([poid, sid, pid, fid, date, expected, qty, "Received" if received else "Open"])
            if received:
                delivered = int(qty*(rng.uniform(.65, .95) if sid % 7 == 0 else rng.choice([.9, 1, 1, 1])))
                deliveries.append([len(deliveries)+1, poid, sid, pid, fid, actual, delivered])
    tables["purchase_orders"] = pd.DataFrame(pos, columns=["po_id", "supplier_id", "product_id", "facility_id", "order_date", "expected_date", "ordered_quantity", "status"])
    tables["supplier_deliveries"] = pd.DataFrame(deliveries, columns=["delivery_id", "po_id", "supplier_id", "product_id", "facility_id", "delivery_date", "delivered_quantity"])
    receipt = tables["supplier_deliveries"].copy()
    receipt["month"] = receipt.delivery_date.dt.to_period("M").dt.to_timestamp()
    receipts = receipt.groupby(["month", "facility_id", "product_id"]).delivered_quantity.sum()
    prod = tables["production"].copy()
    prod["month"] = prod.production_date.dt.to_period("M").dt.to_timestamp()
    produced = prod.set_index(["month", "facility_id", "product_id"]).produced_quantity
    onhand = {(f, p): (5 if f == 5 else 30) for f in range(1, 6) for p in range(1, npd+1)}
    grouped_lines = {key: list(group.itertuples()) for key, group in joined.groupby(["month", "facility_id", "product_id"])}
    snapshots = []
    for month in months:
        for fid in range(1, 6):
            for pid in range(1, npd+1):
                opening = onhand[(fid, pid)]
                pq, rq = int(produced.get((month, fid, pid), 0)), int(receipts.get((month, fid, pid), 0))
                available = opening+pq+rq
                used = 0
                for row in grouped_lines.get((month, fid, pid), []):
                    target = int(row.ordered_quantity*rng.choice([.75, .9, 1, 1, 1, 1]))
                    fulfilled = min(target, available-used)
                    sales.loc[row.Index, "fulfilled_quantity"] = fulfilled
                    used += fulfilled
                closing = available-used
                snapshots.append([len(snapshots)+1, month+pd.offsets.MonthEnd(0), fid, pid, opening, pq, rq, used, closing])
                onhand[(fid, pid)] = closing
    tables["inventory"] = pd.DataFrame(snapshots, columns=["inventory_id", "snapshot_date", "facility_id", "product_id", "opening_quantity", "production_quantity", "receipt_quantity", "consumed_quantity", "on_hand_quantity"])
    tables["order_lines"] = sales
    fulfillment = sales.groupby("order_id").apply(lambda g: bool((g.fulfilled_quantity >= g.ordered_quantity).all()), include_groups=False)
    tables["sales_orders"]["status"] = tables["sales_orders"].order_id.map(fulfillment).map({True: "Fulfilled", False: "Open"})
    shipments = []
    for row in sales.merge(tables["sales_orders"], on="order_id").itertuples():
        if row.fulfilled_quantity <= 0:
            continue
        carrier = int(rng.integers(1, cfg["carriers"]+1))
        delay = int(rng.integers(4, 11) if carrier % 5 == 0 else rng.choice([-1, 0, 0, 0, 1, 3]))
        actual = min(row.required_date+pd.Timedelta(days=delay), as_of)
        shipments.append([len(shipments)+1, row.line_id, row.order_id, row.product_id, row.facility_id, carrier, row.order_date+pd.Timedelta(days=2), row.required_date, actual, row.fulfilled_quantity, row.fulfilled_quantity, f"{CITIES[row.facility_id-1]}-{tables['customers'].loc[row.customer_id-1, 'region']}"])
    tables["shipments"] = pd.DataFrame(shipments, columns=["shipment_id", "line_id", "order_id", "product_id", "facility_id", "carrier_id", "ship_date", "promised_date", "actual_delivery_date", "shipped_quantity", "delivered_quantity", "route"])
    # Defects are isolated copies except category spelling, allowing complete ledger recovery.
    defect_manifest = []
    def bad_copy(table, column, value, defect):
        frame = tables[table]
        sample = frame.iloc[[0]].copy()
        key = frame.columns[0]
        if defect != "duplicate":
            sample[key] = int(frame[key].max())+1000+len(defect_manifest)
        sample[column] = value
        tables[table] = pd.concat([frame, sample], ignore_index=True)
        defect_manifest.append({"table": table, "defect": defect, "column": column, "injected_rows": 1})
    bad_copy("sales_orders", "status", tables["sales_orders"].iloc[0].status, "duplicate")
    bad_copy("order_lines", "ordered_quantity", tables["order_lines"].iloc[0].ordered_quantity, "duplicate")
    bad_copy("customers", "customer_id", None, "missing_id")
    bad_copy("order_lines", "product_id", 999999, "invalid_reference")
    bad_copy("inventory", "on_hand_quantity", -100, "negative_inventory")
    bad_copy("sales_orders", "order_date", "not-a-date", "invalid_date")
    tables["products"].loc[tables["products"].product_id % 10 == 0, "category"] = "  intermediate bulk containers  "
    defect_manifest.append({"table": "products", "defect": "category_case_whitespace", "column": "category", "injected_rows": npd//10})
    for name, frame in tables.items():
        path = root/"data/raw"/SOURCES[name]
        path.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path/f"{name}.csv", index=False, date_format="%Y-%m-%d")
    (root/"data/reference/defect_manifest.json").write_text(json.dumps(defect_manifest, indent=2), encoding="utf-8")
    (root/"data/reference/simulation.json").write_text(json.dumps({"seed": cfg["seed"], "start_date": str(months[0].date()), "as_of": str(as_of.date()), "months": cfg["months"], "synthetic_only": True}, indent=2), encoding="utf-8")
    return tables
