import json
import sqlite3
import numpy as np
import pandas as pd
import pytest
from src.data.generate import generate, CATEGORIES
from src.pipeline.clean import clean_table, curate
from src.pipeline.run import run


def test_source_systems(built):
    root, _, _ = built
    assert {p.name for p in (root/"data/raw").iterdir()} == {"erp", "mes", "wms", "supplier", "logistics"}


def test_minimum_history(built, db):
    row = db.execute("SELECT COUNT(DISTINCT substr(snapshot_date,1,7)) FROM fact_inventory").fetchone()
    assert row[0] == 18


def test_fixed_seed_generation(built, tmp_path):
    root, cfg, _ = built
    generate(tmp_path, cfg)
    for source in (root/"data/raw").rglob("*.csv"):
        assert source.read_bytes() == (tmp_path/"data/raw"/source.relative_to(root/"data/raw")).read_bytes()


def test_defects_manifest_and_rejection(built):
    root, _, report = built
    defects = json.loads((root/"data/reference/defect_manifest.json").read_text())
    assert len(defects) == 7
    assert report["rejected_rows"] == 6
    assert all((root/"outputs/reports"/f"quarantine_{d['table']}.csv").exists() for d in defects)


def test_category_standardization(clean_tables):
    assert set(clean_tables["products"].category) == set(CATEGORIES)


@pytest.mark.parametrize("column,value,reason", [("customer_id", None, "invalid_id"), ("facility_id", 999999, "invalid_reference"), ("order_date", "garbage", "invalid_date"), ("required_date", "2000-01-01", "date_sequence")])
def test_invalid_order_quarantine(clean_tables, column, value, reason):
    raw = clean_tables["sales_orders"].iloc[[0]].copy().astype(object)
    raw.loc[raw.index[0], column] = value
    good, bad = clean_table("sales_orders", raw, clean_tables)
    assert good.empty and len(bad) == 1
    assert reason in bad.iloc[0].rejection_reason


def test_duplicates_keep_first(clean_tables):
    raw = pd.concat([clean_tables["order_lines"].iloc[[0]]]*2, ignore_index=True)
    good, bad = clean_table("order_lines", raw, clean_tables)
    assert len(good) == 1 and len(bad) == 1
    assert "duplicate_primary_key" in bad.iloc[0].rejection_reason


def test_schema_validation(clean_tables):
    with pytest.raises(ValueError, match="missing columns"):
        clean_table("products", clean_tables["products"].drop(columns="standard_cost"), {})


def test_negative_inventory_rejected(clean_tables):
    raw = clean_tables["inventory"].iloc[[0]].copy()
    raw["on_hand_quantity"] = -1
    good, bad = clean_table("inventory", raw, clean_tables)
    assert good.empty and "invalid_nonnegative" in bad.iloc[0].rejection_reason


def test_inventory_ledger_and_continuity(clean_tables):
    inv = clean_tables["inventory"].sort_values(["product_id", "facility_id", "snapshot_date"])
    assert np.array_equal(inv.on_hand_quantity, inv.opening_quantity+inv.production_quantity+inv.receipt_quantity-inv.consumed_quantity)
    prior = inv.groupby(["product_id", "facility_id"]).on_hand_quantity.shift()
    assert (inv.loc[prior.notna(), "opening_quantity"] == prior.dropna()).all()


def test_inventory_receipts_independent_reconciliation(db):
    mismatch = db.execute("""SELECT COUNT(*) FROM fact_inventory i LEFT JOIN
      (SELECT product_id,facility_id,substr(delivery_date,1,7) month,SUM(delivered_quantity) q
       FROM fact_supplier_delivery GROUP BY 1,2,3) r
      ON i.product_id=r.product_id AND i.facility_id=r.facility_id AND substr(i.snapshot_date,1,7)=r.month
      WHERE i.receipt_quantity != COALESCE(r.q,0)""").fetchone()[0]
    assert mismatch == 0


def test_inventory_consumption_independent_reconciliation(db):
    mismatch = db.execute("""SELECT COUNT(*) FROM fact_inventory i LEFT JOIN
      (SELECT product_id,facility_id,substr(order_date,1,7) month,SUM(fulfilled_quantity) q
       FROM fact_sales_order GROUP BY 1,2,3) s
      ON i.product_id=s.product_id AND i.facility_id=s.facility_id AND substr(i.snapshot_date,1,7)=s.month
      WHERE i.consumed_quantity != COALESCE(s.q,0)""").fetchone()[0]
    assert mismatch == 0


def test_supplier_delivery_matches_po(db):
    assert db.execute("SELECT COUNT(*) FROM fact_supplier_delivery d JOIN fact_purchase_order p USING(po_id) WHERE d.supplier_id!=p.supplier_id OR d.product_id!=p.product_id OR d.facility_id!=p.facility_id").fetchone()[0] == 0


def test_supplier_products_qualified(db):
    assert db.execute("SELECT COUNT(*) FROM fact_purchase_order p LEFT JOIN bridge_supplier_product b USING(supplier_id,product_id) WHERE b.supplier_product_id IS NULL").fetchone()[0] == 0


def test_production_tracks_demand(db):
    rows = db.execute("SELECT p.planned_quantity,COALESCE(s.q,0) FROM fact_production p LEFT JOIN (SELECT product_id,facility_id,substr(order_date,1,7) m,SUM(ordered_quantity) q FROM fact_sales_order GROUP BY 1,2,3) s ON p.product_id=s.product_id AND p.facility_id=s.facility_id AND substr(p.production_date,1,7)=s.m").fetchall()
    x, y = np.array([tuple(r) for r in rows]).T
    assert np.corrcoef(x, y)[0, 1] > .85


def test_facility_five_shortfall(db):
    row = db.execute("SELECT SUM(planned_quantity)*1.0/SUM(demand_quantity) FROM (SELECT facility_id,SUM(planned_quantity) planned_quantity FROM fact_production GROUP BY facility_id) p JOIN (SELECT facility_id,SUM(ordered_quantity) demand_quantity FROM fact_sales_order GROUP BY facility_id) s USING(facility_id) WHERE facility_id=5").fetchone()[0]
    assert row < .75


def test_foreign_key_integrity(db):
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_sql_check_constraints(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE fact_inventory SET on_hand_quantity=-1 WHERE inventory_id=1")
    db.rollback()


def test_sql_reference_constraints(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE fact_sales_order SET product_id=999999 WHERE line_id=1")
    db.rollback()


def test_curated_grain(clean_tables):
    tables = curate(clean_tables)
    assert len(tables["fact_sales_order"]) == len(clean_tables["order_lines"])
    assert tables["fact_sales_order"].line_id.is_unique


def test_pipeline_idempotency_and_status_preservation(built):
    from contextlib import closing
    root, cfg, previous = built
    manifest_before = json.loads((root/"outputs/powerbi/manifest.json").read_text())
    result = run(root, regenerate=False, cfg=cfg)
    assert result["record_counts"] == previous["record_counts"]
    assert json.loads((root/"outputs/powerbi/manifest.json").read_text()) == manifest_before
    with closing(sqlite3.connect(root/"database/control_tower.sqlite")) as db:
        eid = db.execute("SELECT exception_id FROM supply_chain_exception LIMIT 1").fetchone()[0]
        db.execute("UPDATE supply_chain_exception SET status='Accepted' WHERE exception_id=?", (eid,))
        db.commit()
    run(root, regenerate=False, cfg=cfg)
    with closing(sqlite3.connect(root/"database/control_tower.sqlite")) as db:
        assert db.execute("SELECT status FROM supply_chain_exception WHERE exception_id=?", (eid,)).fetchone()[0] == "Accepted"
        db.execute("UPDATE supply_chain_exception SET status='Open' WHERE exception_id=?", (eid,))
        db.commit()


def test_exports_match_warehouse(built, db):
    from src.reporting.export import EXPORTS
    for table, file in EXPORTS.items():
        frame = pd.read_csv(built[0]/"outputs/powerbi"/(file+".csv"))
        assert len(frame) == db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert list(frame.columns) == [r[1] for r in db.execute(f"PRAGMA table_info({table})")]


def test_failed_load_preserves_previous_database(built, tmp_path):
    from src.config import prepare
    from src.db.warehouse import load
    prepare(tmp_path)
    tables = {name: pd.read_csv(built[0]/"data/curated"/f"{name}.csv") for name in built[2]["record_counts"]}
    load(tmp_path, tables)
    target = tmp_path/"database/control_tower.sqlite"
    previous_bytes = target.read_bytes()
    tables["fact_sales_order"].loc[0, "backlog_quantity"] += 1
    with pytest.raises(sqlite3.IntegrityError):
        load(tmp_path, tables)
    assert target.read_bytes() == previous_bytes
    assert not (tmp_path/"database/control_tower.build.sqlite").exists()


def test_dictionary_covers_actual_schema(built):
    from scripts.document_results import dictionary
    dictionary(built[0])
    text = (built[0]/"DATA_DICTIONARY.md").read_text(encoding="utf-8")
    assert all(f"## {name}" in text for name in built[2]["record_counts"])
    assert "Future actuals" in text
