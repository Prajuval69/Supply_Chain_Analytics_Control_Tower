"""Profile untouched inputs, standardize types, quarantine invalid records."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.data.contracts import CONTRACTS, SOURCES, TEXT_FIELDS
from src.data.generate import CATEGORIES


def profile(frame: pd.DataFrame) -> dict:
    return {"rows": len(frame), "exact_duplicate_rows": int(frame.duplicated().sum()),
            "columns": {c: {"dtype": str(frame[c].dtype), "nulls": int(frame[c].isna().sum()),
                            "distinct": int(frame[c].nunique())} for c in frame}}


def clean_table(name: str, raw: pd.DataFrame, parents: dict[str, pd.DataFrame]):
    key, dates, numerics, foreign = CONTRACTS[name]
    required = {key, *dates, *numerics, *foreign, *TEXT_FIELDS.get(name, [])}
    missing = required-set(raw.columns)
    if missing:
        raise ValueError(f"{name}: missing columns {sorted(missing)}")
    df = raw.copy()
    reasons = pd.Series("", index=df.index)
    def reject(mask, reason):
        nonlocal reasons
        reasons.loc[mask] += reason+";"
    keys = [c for c in df if c.endswith("_id")]
    for c in keys:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        reject(df[c].isna() | (df[c] <= 0) | (df[c] % 1 != 0), f"invalid_id:{c}")
    reject(df[key].duplicated(keep="first") & df[key].notna(), "duplicate_primary_key")
    for c in dates:
        df[c] = pd.to_datetime(df[c], errors="coerce", format="mixed")
        reject(df[c].isna(), f"invalid_date:{c}")
    for c in numerics:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        reject(df[c].isna() | ~np.isfinite(df[c]) | (df[c] < 0), f"invalid_nonnegative:{c}")
    for c, parent in foreign.items():
        pk = CONTRACTS[parent][0]
        reject(~df[c].isin(parents[parent][pk]), f"invalid_reference:{c}")
    for c in df.select_dtypes("object"):
        df[c] = df[c].str.strip()
        reject(df[c].isna() | df[c].eq(""), f"missing_text:{c}")
    if name == "products":
        df["category"] = df.category.str.casefold().map({x.casefold(): x for x in CATEGORIES})
        reject(df.category.isna(), "unknown_category")
        reject(df.standard_cost <= 0, "invalid_cost")
    if name in ("sales_orders", "purchase_orders"):
        end = "required_date" if name == "sales_orders" else "expected_date"
        reject(df[end] < df.order_date, "date_sequence")
        reject(~df.status.isin(["Fulfilled", "Open"] if name == "sales_orders" else ["Received", "Open"]), "invalid_status")
    if name == "order_lines":
        reject((df.ordered_quantity <= 0) | (df.fulfilled_quantity > df.ordered_quantity), "quantity_bounds")
    if name == "inventory":
        balance = df.opening_quantity+df.production_quantity+df.receipt_quantity-df.consumed_quantity
        reject(~np.isclose(balance, df.on_hand_quantity, equal_nan=False), "inventory_balance")
    if name == "supplier_deliveries":
        po = parents["purchase_orders"].set_index("po_id")
        for c in ("supplier_id", "product_id", "facility_id"):
            reject(df[c].ne(df.po_id.map(po[c])), f"po_mismatch:{c}")
        reject(df.delivery_date < df.po_id.map(po.order_date), "delivery_before_order")
    if name == "shipments":
        line = parents["order_lines"].set_index("line_id")
        order = parents["sales_orders"].set_index("order_id")
        for c in ("order_id", "product_id"):
            reject(df[c].ne(df.line_id.map(line[c])), f"line_mismatch:{c}")
        reject(df.facility_id.ne(df.order_id.map(order.facility_id)), "shipment_facility_mismatch")
        reject((df.ship_date < df.order_id.map(order.order_date)) | (df.actual_delivery_date < df.ship_date), "shipment_date_sequence")
        reject((df.delivered_quantity > df.shipped_quantity) | (df.shipped_quantity > df.line_id.map(line.fulfilled_quantity)), "shipment_quantity_bounds")
    good = df.loc[reasons.eq("")].copy()
    for c in keys:
        good[c] = good[c].astype("int64")
    quarantine = raw.loc[reasons.ne("")].copy()
    quarantine["rejection_reason"] = reasons.loc[reasons.ne("")]
    return good, quarantine


def ingest_clean(root: Path) -> tuple[dict, dict]:
    clean, quality = {}, {}
    for name in CONTRACTS:
        raw = pd.read_csv(root/"data/raw"/SOURCES[name]/f"{name}.csv")
        raw.to_csv(root/"data/staging"/f"{name}.csv", index=False)
        df, quarantine = clean_table(name, raw, clean)
        clean[name] = df
        df.to_csv(root/"data/processed"/f"{name}.csv", index=False, date_format="%Y-%m-%d")
        quarantine.to_csv(root/"outputs/reports"/f"quarantine_{name}.csv", index=False)
        quality[name] = {"raw": profile(raw), "cleaned": profile(df), "rejected_rows": len(quarantine),
                         "reasons": quarantine.rejection_reason.value_counts().to_dict()}
    (root/"outputs/reports/data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    return clean, quality


def curate(tables: dict) -> dict:
    result = {f"dim_{singular}": tables[plural].copy() for singular, plural in
              [("customer", "customers"), ("product", "products"), ("supplier", "suppliers"), ("facility", "facilities"), ("carrier", "carriers")]}
    result["bridge_supplier_product"] = tables["supplier_products"].copy()
    sales = tables["order_lines"].merge(tables["sales_orders"], on="order_id", validate="many_to_one")
    sales["backlog_quantity"] = sales.ordered_quantity-sales.fulfilled_quantity
    result["fact_sales_order"] = sales
    for source, fact in [("production", "production"), ("inventory", "inventory"), ("purchase_orders", "purchase_order")]:
        result[f"fact_{fact}"] = tables[source].copy()
    deliveries = tables["supplier_deliveries"].merge(tables["purchase_orders"][["po_id", "order_date", "expected_date", "ordered_quantity"]], on="po_id", validate="many_to_one")
    deliveries["lead_time_days"] = (deliveries.delivery_date-deliveries.order_date).dt.days
    deliveries["delay_days"] = (deliveries.delivery_date-deliveries.expected_date).dt.days.clip(lower=0)
    deliveries["on_time"] = (deliveries.delivery_date <= deliveries.expected_date).astype(int)
    deliveries["in_full"] = (deliveries.delivered_quantity >= deliveries.ordered_quantity).astype(int)
    deliveries["otif"] = deliveries.on_time*deliveries.in_full
    result["fact_supplier_delivery"] = deliveries
    shipments = tables["shipments"].merge(tables["order_lines"][["line_id", "ordered_quantity"]], on="line_id", validate="many_to_one")
    shipments["delay_days"] = (shipments.actual_delivery_date-shipments.promised_date).dt.days.clip(lower=0)
    shipments["on_time"] = (shipments.actual_delivery_date <= shipments.promised_date).astype(int)
    shipments["in_full"] = (shipments.delivered_quantity >= shipments.ordered_quantity).astype(int)
    shipments["otif"] = shipments.on_time*shipments.in_full
    result["fact_shipment"] = shipments
    min_date = tables["sales_orders"].order_date.min().replace(day=1)
    max_date = tables["inventory"].snapshot_date.max()+pd.offsets.MonthEnd(3)
    dates = pd.DataFrame({"date": pd.date_range(min_date, max_date)})
    dates["date_id"] = dates.date.dt.strftime("%Y%m%d").astype(int)
    dates["year"], dates["month"], dates["quarter"] = dates.date.dt.year, dates.date.dt.month, dates.date.dt.quarter
    dates["month_start"] = dates.date.dt.to_period("M").dt.to_timestamp()
    result["dim_date"] = dates[["date_id", "date", "year", "month", "quarter", "month_start"]]
    return result
