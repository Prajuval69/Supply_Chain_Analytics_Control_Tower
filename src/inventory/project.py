import math
import pandas as pd


def project(current, receipts, demand):
    return float(current+receipts-demand)


def stockout_date(start, opening, receipts, demand, threshold=0):
    start = pd.Timestamp(start)
    days = (start+pd.offsets.MonthEnd(0)).day
    available = opening+receipts
    if available <= threshold:
        return str(start.date())
    if demand <= 0 or available-demand > threshold:
        return None
    day = max(1, min(days, math.ceil((available-threshold)/demand*days)))
    return str((start+pd.Timedelta(days=day-1)).date())


def projections(analytics: dict, curated: dict, forecast: pd.DataFrame, cfg: dict):
    hist = analytics["agg_demand"]
    recent = hist[hist.month >= hist.month.max()-pd.offsets.MonthBegin(2)].groupby(["product_id", "facility_id"]).demand_quantity.sum()
    shares = recent/recent.groupby(level=0).transform("sum").replace(0, float("nan"))
    pos = curated["fact_purchase_order"]
    open_po = pos[pos.status == "Open"].copy()
    as_of = curated["fact_inventory"].snapshot_date.max()
    # Overdue outstanding receipts assumed at next month start, exposed as assumptions.
    open_po["receipt_month"] = open_po.expected_date.clip(lower=as_of+pd.Timedelta(days=1)).dt.to_period("M").astype(str)
    receipt = open_po.groupby(["product_id", "facility_id", "receipt_month"]).ordered_quantity.sum()
    rows = []
    for inv in analytics["agg_inventory"].itertuples():
        opening = float(inv.on_hand_quantity)
        for f in forecast[forecast.product_id == inv.product_id].sort_values("horizon").itertuples():
            share = shares.get((inv.product_id, inv.facility_id), .2)
            if pd.isna(share):
                share = .2
            demand = float(f.prediction*share)
            expected = float(receipt.get((inv.product_id, inv.facility_id, f.forecast_date[:7]), 0))
            ending = project(opening, expected, demand)
            days = pd.Timestamp(f.forecast_date).days_in_month
            doi = max(0, ending)/(demand/days) if demand > 0 else None
            risk = ending <= cfg["stockout_threshold"]
            excess = (doi is not None and doi > cfg["excess_days"]) or (demand == 0 and ending > 0)
            replenishment = max(0, math.ceil(demand+cfg["stockout_threshold"]-ending)) if risk else 0
            rows.append({"product_id": inv.product_id, "facility_id": inv.facility_id, "forecast_date": f.forecast_date, "horizon": f.horizon, "opening_inventory": opening, "expected_receipts": expected, "forecast_demand": demand, "projected_ending_inventory": ending, "stockout_flag": int(risk), "stockout_date": stockout_date(f.forecast_date, opening, expected, demand, cfg["stockout_threshold"]), "days_of_inventory": doi, "excess_inventory_flag": int(excess), "replenishment_quantity": replenishment, "recommendation": "Expedite supply or schedule production" if risk else ("Reduce replenishment and rebalance stock" if excess else "Maintain planned replenishment")})
            opening = ending
    return pd.DataFrame(rows)

