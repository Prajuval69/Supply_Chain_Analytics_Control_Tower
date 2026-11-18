import json
import sqlite3
from contextlib import closing
from pathlib import Path
import numpy as np
import pandas as pd

PRIMARY = {
    "dim_date": ["date_id"], "dim_customer": ["customer_id"], "dim_product": ["product_id"],
    "dim_supplier": ["supplier_id"], "dim_facility": ["facility_id"], "dim_carrier": ["carrier_id"],
    "bridge_supplier_product": ["supplier_product_id"], "fact_sales_order": ["line_id"],
    "fact_production": ["production_id"], "fact_inventory": ["inventory_id"],
    "fact_purchase_order": ["po_id"], "fact_supplier_delivery": ["delivery_id"], "fact_shipment": ["shipment_id"],
    "agg_demand": ["month", "product_id", "facility_id"], "agg_inventory": ["product_id", "facility_id"],
    "agg_supplier": ["supplier_id"], "agg_logistics": ["carrier_id", "facility_id", "route"],
    "agg_facility": ["facility_id"], "forecast_demand": ["product_id", "horizon"],
    "forecast_validation": ["product_id", "model_name", "train_end", "horizon"],
    "forecast_test": ["product_id", "horizon"],
    "forecast_model_metrics": ["product_id", "model_name"], "projected_inventory": ["product_id", "facility_id", "horizon"],
    "supply_chain_exception": ["exception_id"], "executive_kpis": ["as_of"],
}
DIMENSIONS = {"customer_id": "dim_customer", "product_id": "dim_product", "supplier_id": "dim_supplier", "facility_id": "dim_facility", "carrier_id": "dim_carrier"}


def ddl(tables: dict) -> str:
    """Compile table contracts to inspectable SQL with keys, checks and indexes."""
    statements = ["PRAGMA foreign_keys = ON;"]
    for name, frame in tables.items():
        columns, constraints = [], []
        for c in frame:
            dtype = frame[c].dtype
            sqltype = "INTEGER" if pd.api.types.is_integer_dtype(dtype) else ("REAL" if pd.api.types.is_numeric_dtype(dtype) else "TEXT")
            if c.endswith("_id") and c not in ("exception_id", "date_id"):
                sqltype = "INTEGER"
            required = name.startswith(("dim_", "fact_", "bridge_")) or c in PRIMARY[name]
            columns.append(f'"{c}" {sqltype}'+(" NOT NULL" if required else ""))
            if c in DIMENSIONS and name != DIMENSIONS[c]:
                constraints.append(f'FOREIGN KEY ("{c}") REFERENCES {DIMENSIONS[c]} ("{c}")')
            if name.startswith("fact_") and (c.endswith("_quantity") or c in ("delay_days", "lead_time_days")):
                constraints.append(f'CHECK ("{c}" >= 0)')
            if c in ("otif", "on_time", "in_full", "stockout_flag", "excess_inventory_flag"):
                constraints.append(f'CHECK ("{c}" IN (0,1))')
            if name.startswith("fact_") and c.endswith("date"):
                constraints.append(f'FOREIGN KEY ("{c}") REFERENCES dim_date (date)')
        constraints.append("PRIMARY KEY ("+", ".join(f'"{c}"' for c in PRIMARY[name])+")")
        if name == "dim_date":
            constraints.append("UNIQUE (date)")
        if name == "fact_inventory":
            constraints.extend(["UNIQUE(snapshot_date, product_id, facility_id)", "CHECK(on_hand_quantity = opening_quantity + production_quantity + receipt_quantity - consumed_quantity)"])
        if name == "fact_sales_order":
            constraints.extend(["CHECK(ordered_quantity > 0)", "CHECK(fulfilled_quantity <= ordered_quantity)", "CHECK(backlog_quantity = ordered_quantity - fulfilled_quantity)", "CHECK(required_date >= order_date)", "CHECK(status IN ('Open','Fulfilled'))"])
        if name == "bridge_supplier_product":
            constraints.append("UNIQUE(supplier_id,product_id)")
        if name == "fact_purchase_order":
            constraints.extend(["CHECK(expected_date >= order_date)", "CHECK(status IN ('Open','Received'))"])
        if name == "fact_supplier_delivery":
            constraints.extend(["FOREIGN KEY(po_id) REFERENCES fact_purchase_order(po_id)", "UNIQUE(po_id)", "CHECK(delivery_date >= order_date)", "CHECK(otif = on_time * in_full)"])
        if name == "fact_shipment":
            constraints.extend(["FOREIGN KEY(line_id) REFERENCES fact_sales_order(line_id)", "UNIQUE(line_id)", "CHECK(actual_delivery_date >= ship_date)", "CHECK(delivered_quantity <= shipped_quantity)", "CHECK(otif = on_time * in_full)"])
        if name == "supply_chain_exception":
            constraints.extend(["CHECK(status IN ('Open','Investigating','Resolved','Accepted'))", "CHECK(severity IN ('Critical','High','Medium','Low'))"])
        statements.append(f"CREATE TABLE {name} (\n  "+",\n  ".join(columns+constraints)+"\n);")
        for c in frame:
            if c in DIMENSIONS or (name.startswith("fact_") and c.endswith("date")):
                statements.append(f'CREATE INDEX ix_{name}_{c} ON {name}("{c}");')
    statements.append("CREATE INDEX ix_exception_status_severity ON supply_chain_exception(status,severity);")
    statements.append("CREATE INDEX ix_sales_order_id ON fact_sales_order(order_id);")
    return "\n\n".join(statements)+"\n"


def serialized(frame):
    frame = frame.copy()
    for c in frame:
        if pd.api.types.is_datetime64_any_dtype(frame[c]):
            frame[c] = frame[c].dt.strftime("%Y-%m-%d")
    def convert(x):
        if pd.isna(x):
            return None
        if isinstance(x, np.generic):
            return x.item()
        return x
    return [tuple(convert(x) for x in row) for row in frame.itertuples(index=False, name=None)]


def previous_statuses(path: Path):
    if not path.exists():
        return {}
    with closing(sqlite3.connect(path)) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='supply_chain_exception'").fetchone():
            return dict(db.execute("SELECT exception_id,status FROM supply_chain_exception"))
    return {}


def load(root: Path, tables: dict) -> dict:
    target = root/"database/control_tower.sqlite"
    temp = root/"database/control_tower.build.sqlite"
    if temp.exists():
        temp.unlink()
    sql = ddl(tables)
    (root/"database/schema.sql").write_text(sql, encoding="utf-8")
    try:
        with closing(sqlite3.connect(temp)) as db, db:
            db.executescript(sql)
            # Defer references to permit dimension calendar load after facts in mapping.
            db.execute("PRAGMA defer_foreign_keys=ON")
            for name, frame in tables.items():
                placeholders = ",".join("?" for _ in frame.columns)
                quoted = ",".join(f'"{c}"' for c in frame.columns)
                db.executemany(f"INSERT INTO {name} ({quoted}) VALUES ({placeholders})", serialized(frame))
            fk = db.execute("PRAGMA foreign_key_check").fetchall()
            if fk:
                raise ValueError(f"Referential integrity failed: {fk[:5]}")
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(integrity)
            counts = {name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in tables}
        temp.replace(target)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    report = {"integrity_check": integrity, "foreign_key_violations": len(fk), "record_counts": counts}
    (root/"outputs/reports/database_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
