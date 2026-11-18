import math
import numpy as np
import pandas as pd
import pytest
from src.analytics.metrics import otif, fill_rate, turnover, ratio, order_summary
from src.forecasting.models import error_metrics, predict, forecast
from src.inventory.project import project, stockout_date
from src.exceptions.engine import ACTIONS, exception_id


@pytest.mark.parametrize("arrival,quantity,expected", [("2025-01-10", 100, True), ("2025-01-11", 100, False), ("2025-01-10", 99, False), ("2025-01-11", 99, False)])
def test_otif_requires_both(arrival, quantity, expected):
    assert otif(pd.Timestamp(arrival), pd.Timestamp("2025-01-10"), quantity, 100) is expected


def test_fill_rate_weighted():
    assert fill_rate([90, 1], [100, 10]) == pytest.approx(91/110)


def test_turnover_cost_weighted():
    assert turnover([10, 20], [2, 5], 60) == 2


def test_zero_denominator_is_missing():
    assert ratio(0, 0) is None
    assert fill_rate([], []) is None


def test_order_count_is_distinct_and_overdue():
    sales = pd.DataFrame({"order_id": [1, 1, 2], "ordered_quantity": [10, 20, 5], "fulfilled_quantity": [10, 19, 5], "required_date": pd.to_datetime(["2025-01-01"]*3)})
    result = order_summary(sales, pd.Timestamp("2025-01-02"))
    assert result == {"order_count": 2, "fulfilled_orders": 1, "open_orders": 1, "overdue_orders": 1, "fulfillment_rate": .5, "backlog_quantity": 1, "fill_rate": 34/35}


def test_demand_reconciles_sql(db):
    raw = db.execute("SELECT SUM(ordered_quantity) FROM fact_sales_order").fetchone()[0]
    agg = db.execute("SELECT SUM(demand_quantity) FROM agg_demand").fetchone()[0]
    assert raw == agg


def test_dense_demand_calendar(built, db):
    cfg = built[1]
    assert db.execute("SELECT COUNT(*) FROM agg_demand").fetchone()[0] == cfg["months"]*cfg["products"]*5
    assert db.execute("SELECT COUNT(*) FROM agg_demand WHERE demand_quantity=0").fetchone()[0] > 0


def test_supplier_otif_sql(db):
    for row in db.execute("SELECT supplier_id,supplier_otif FROM agg_supplier WHERE deliveries>0"):
        actual = db.execute("SELECT AVG(CASE WHEN delivery_date<=expected_date AND delivered_quantity>=ordered_quantity THEN 1.0 ELSE 0.0 END) FROM fact_supplier_delivery WHERE supplier_id=?", (row[0],)).fetchone()[0]
        assert row[1] == pytest.approx(actual)


def test_logistics_weighted_otif(db):
    x = db.execute("SELECT SUM(otif_count)*1.0/SUM(shipments) FROM agg_logistics").fetchone()[0]
    y = db.execute("SELECT AVG(CASE WHEN actual_delivery_date<=promised_date AND delivered_quantity>=ordered_quantity THEN 1.0 ELSE 0.0 END) FROM fact_shipment").fetchone()[0]
    assert x == pytest.approx(y)


def test_inventory_turnover_sql_independent(db):
    proxy = db.execute("SELECT SUM(s.fulfilled_quantity*p.standard_cost) FROM fact_sales_order s JOIN dim_product p USING(product_id)").fetchone()[0]
    average = db.execute("SELECT AVG(value) FROM (SELECT snapshot_date,SUM(on_hand_quantity*standard_cost) value FROM fact_inventory JOIN dim_product USING(product_id) GROUP BY snapshot_date)").fetchone()[0]
    actual = db.execute("SELECT inventory_turnover FROM executive_kpis").fetchone()[0]
    assert actual == pytest.approx(proxy/average)


def test_forecast_metrics_known_values():
    m = error_metrics([10, 0, 20], [8, 1, 23])
    assert m["mae"] == 2
    assert m["rmse"] == pytest.approx(math.sqrt(14/3))
    assert m["mape"] == pytest.approx(17.5)
    assert m["mape_eligible_count"] == 2


def test_all_zero_mape():
    assert error_metrics([0, 0], [1, 2])["mape"] is None


@pytest.mark.parametrize("actual,predicted", [([], []), ([1], [1, 2]), ([float('nan')], [1])])
def test_metrics_reject_invalid(actual, predicted):
    with pytest.raises(ValueError):
        error_metrics(actual, predicted)


def test_baseline_predicts_last_three_average():
    assert np.array_equal(predict(np.arange(1, 19), 3, "moving_average_3"), [17, 17, 17])


def test_regression_captures_trend_and_seasonality():
    t = np.arange(30)
    y = 100+3*t+20*np.sin(2*np.pi*t/12)
    expected = 100+3*np.arange(30, 33)+20*np.sin(2*np.pi*np.arange(30, 33)/12)
    assert error_metrics(expected, predict(y, 3, "trend_seasonal_regression"))["mae"] < 2


def test_forecast_nonnegative_and_horizons(db):
    assert db.execute("SELECT COUNT(*) FROM forecast_demand WHERE prediction<0 OR horizon NOT IN(1,2,3) OR actual IS NOT NULL").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(DISTINCT horizon) FROM forecast_demand").fetchone()[0] == 3


def test_validation_no_future_data(db):
    for row in db.execute("SELECT product_id,train_end,horizon,prediction,model_name FROM forecast_validation"):
        hist = [r[0] for r in db.execute("SELECT SUM(demand_quantity) FROM agg_demand WHERE product_id=? AND month<=? GROUP BY month ORDER BY month", (row[0], row[1]))]
        assert row[3] == pytest.approx(predict(hist, 3, row[4])[row[2]-1])


def test_untouched_holdout_excluded_from_selection(db):
    test_first = db.execute("SELECT MIN(forecast_date) FROM forecast_test").fetchone()[0]
    validation_last = db.execute("SELECT MAX(forecast_date) FROM forecast_validation").fetchone()[0]
    assert validation_last < test_first
    assert db.execute("SELECT COUNT(*) FROM forecast_test WHERE forecast_date<=train_end").fetchone()[0] == 0


def test_model_selection_by_validation_mae(db):
    assert db.execute("SELECT COUNT(*) FROM forecast_model_metrics winner JOIN forecast_model_metrics other USING(product_id) WHERE winner.selected=1 AND winner.mae>other.mae").fetchone()[0] == 0


def test_model_selection_not_affected_by_test_actuals():
    dates = pd.date_range("2024-01-01", periods=30, freq="MS")
    demand = pd.DataFrame({"product_id": 1, "month": dates, "demand_quantity": 100+np.arange(30)*2})
    _, _, models_before, _ = forecast(demand)
    demand.loc[27:, "demand_quantity"] = 100000
    _, _, models_after, _ = forecast(demand)
    pd.testing.assert_frame_equal(models_before, models_after)


def test_projection_formula():
    assert project(100, 20, 130) == -10


def test_stockout_exact_boundary_date():
    assert stockout_date("2026-10-01", 31, 0, 31) == "2026-10-31"
    assert stockout_date("2026-10-01", 0, 0, 31) == "2026-10-01"
    assert stockout_date("2026-10-01", 100, 0, 31) is None


def test_projection_balance_and_carry(db):
    rows = db.execute("SELECT * FROM projected_inventory ORDER BY product_id,facility_id,horizon").fetchall()
    prior = {}
    for r in rows:
        assert r["projected_ending_inventory"] == pytest.approx(r["opening_inventory"]+r["expected_receipts"]-r["forecast_demand"])
        pair = r["product_id"], r["facility_id"]
        if pair in prior:
            assert r["opening_inventory"] == prior[pair]
        prior[pair] = r["projected_ending_inventory"]


def test_forecast_allocation_reconciles(db):
    mismatch = db.execute("SELECT COUNT(*) FROM forecast_demand f JOIN (SELECT product_id,horizon,SUM(forecast_demand) q FROM projected_inventory GROUP BY 1,2) p USING(product_id,horizon) WHERE abs(f.prediction-p.q)>0.000001").fetchone()[0]
    assert mismatch == 0


def test_stockout_flags_and_recommendations(db):
    assert db.execute("SELECT COUNT(*) FROM projected_inventory WHERE stockout_flag != (projected_ending_inventory<=0)").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM projected_inventory WHERE stockout_flag=1 AND (stockout_date IS NULL OR replenishment_quantity<=0)").fetchone()[0] == 0


def test_exception_id_stable_and_distinct():
    assert exception_id("STOCKOUT_RISK", "P1-F1") == exception_id("STOCKOUT_RISK", "P1-F1")
    assert exception_id("STOCKOUT_RISK", "P1-F1") != exception_id("EXCESS_INVENTORY", "P1-F1")


def test_all_exception_types_are_generated(db):
    assert {r[0] for r in db.execute("SELECT DISTINCT type FROM supply_chain_exception")} == set(ACTIONS)


def test_exceptions_have_evidence_and_actions(db):
    rows = db.execute("SELECT * FROM supply_chain_exception").fetchall()
    assert len(rows) > 0
    for r in rows:
        assert r["recommended_action"] == ACTIONS[r["type"]]
        assert r["severity"] in ["Critical", "High", "Medium", "Low"]
        assert r["metric"] and r["reference"] and r["status"] in ["Open", "Investigating", "Resolved", "Accepted"]
        assert all(r[x] is not None for x in ["actual_value", "expected_value", "threshold"])


def test_exception_threshold_direction(db):
    for r in db.execute("SELECT * FROM supply_chain_exception"):
        if r["type"] in ["STOCKOUT_RISK", "LOW_SUPPLIER_OTIF", "PRODUCTION_SHORTFALL"]:
            assert r["actual_value"] <= r["threshold"]
        else:
            assert r["actual_value"] > r["threshold"]


def test_facility_sums_reconcile(db):
    for f in db.execute("SELECT * FROM agg_facility"):
        demand, backlog = db.execute("SELECT SUM(ordered_quantity),SUM(ordered_quantity-fulfilled_quantity) FROM fact_sales_order WHERE facility_id=?", (f["facility_id"],)).fetchone()
        assert f["demand_quantity"] == demand and f["backlog_quantity"] == backlog
