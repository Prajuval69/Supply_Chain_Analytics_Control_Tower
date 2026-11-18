import numpy as np
import pandas as pd


def ratio(numerator, denominator):
    return float(numerator/denominator) if denominator else None


def otif(delivered_date, promised_date, delivered_quantity, required_quantity):
    return bool(delivered_date <= promised_date and delivered_quantity >= required_quantity)


def fill_rate(delivered_quantity, ordered_quantity):
    return ratio(sum(delivered_quantity), sum(ordered_quantity))


def turnover(fulfilled_quantity, standard_cost, average_inventory_value):
    """Synthetic fulfilled-units times standard-cost COGS proxy; not annualized."""
    return ratio(float(np.dot(fulfilled_quantity, standard_cost)), average_inventory_value)


def order_summary(sales: pd.DataFrame, as_of) -> dict:
    orders = sales.groupby("order_id").agg(ordered=("ordered_quantity", "sum"), fulfilled=("fulfilled_quantity", "sum"), required=("required_date", "first"))
    done = orders.fulfilled >= orders.ordered
    return {"order_count": len(orders), "fulfilled_orders": int(done.sum()), "open_orders": int((~done).sum()),
            "overdue_orders": int((~done & (orders.required < as_of)).sum()), "fulfillment_rate": ratio(done.sum(), len(orders)),
            "backlog_quantity": int((orders.ordered-orders.fulfilled).sum()),
            "fill_rate": ratio(orders.fulfilled.sum(), orders.ordered.sum())}


def calculate(t: dict, cfg: dict) -> dict[str, pd.DataFrame]:
    sales = t["fact_sales_order"].copy()
    as_of = t["fact_inventory"].snapshot_date.max()
    sales["month"] = sales.order_date.dt.to_period("M").dt.to_timestamp()
    months = pd.date_range(sales.month.min(), as_of.replace(day=1), freq="MS")
    # Dense calendar preserves zero-demand months for volatility and forecasting.
    grid = pd.MultiIndex.from_product([months, t["dim_product"].product_id, t["dim_facility"].facility_id], names=["month", "product_id", "facility_id"])
    demand = sales.groupby(["month", "product_id", "facility_id"]).agg(demand_quantity=("ordered_quantity", "sum"), fulfilled_quantity=("fulfilled_quantity", "sum"), backlog_quantity=("backlog_quantity", "sum")).reindex(grid, fill_value=0).reset_index()
    demand = demand.sort_values(["product_id", "facility_id", "month"])
    demand["previous_demand"] = demand.groupby(["product_id", "facility_id"]).demand_quantity.shift()
    demand["demand_growth"] = (demand.demand_quantity-demand.previous_demand)/demand.previous_demand.replace(0, np.nan)
    volatility = demand.groupby(["product_id", "facility_id"]).demand_quantity.agg(["mean", "std"])
    volatility["demand_volatility"] = volatility["std"]/volatility["mean"].replace(0, np.nan)
    demand = demand.merge(volatility[["demand_volatility"]], on=["product_id", "facility_id"], validate="many_to_one")
    inv = t["fact_inventory"]
    latest = inv[inv.snapshot_date == as_of].copy()
    avg = inv.groupby(["product_id", "facility_id"]).agg(average_inventory=("on_hand_quantity", "mean"), stockout_count=("on_hand_quantity", lambda x: int((x <= cfg["stockout_threshold"]).sum())))
    totals = sales.groupby(["product_id", "facility_id"]).agg(demand_quantity=("ordered_quantity", "sum"), fulfilled_quantity=("fulfilled_quantity", "sum"))
    health = latest.merge(avg, on=["product_id", "facility_id"]).merge(totals, on=["product_id", "facility_id"], how="left").merge(t["dim_product"][["product_id", "standard_cost"]], on="product_id")
    health[["demand_quantity", "fulfilled_quantity"]] = health[["demand_quantity", "fulfilled_quantity"]].fillna(0)
    days = (as_of-sales.month.min()).days+1
    health["average_daily_demand"] = health.demand_quantity/days
    health["days_of_inventory"] = health.average_inventory/health.average_daily_demand.replace(0, np.nan)
    health["current_days_of_inventory"] = health.on_hand_quantity/health.average_daily_demand.replace(0, np.nan)
    health["inventory_value"] = health.on_hand_quantity*health.standard_cost
    health["average_inventory_value"] = health.average_inventory*health.standard_cost
    health["synthetic_cogs_proxy"] = health.fulfilled_quantity*health.standard_cost
    health["inventory_turnover"] = health.synthetic_cogs_proxy/health.average_inventory_value.replace(0, np.nan)
    health["excess_inventory"] = ((health.current_days_of_inventory > cfg["excess_days"]) | ((health.average_daily_demand == 0) & (health.on_hand_quantity > 0))).astype(int)
    supplier = t["fact_supplier_delivery"].groupby("supplier_id").agg(deliveries=("delivery_id", "count"), otif_count=("otif", "sum"), on_time_count=("on_time", "sum"), average_lead_time=("lead_time_days", "mean"), lead_time_variance=("lead_time_days", "var"), late_count=("delay_days", lambda x: int((x > 0).sum())), delivered_quantity=("delivered_quantity", "sum"), ordered_quantity=("ordered_quantity", "sum")).reset_index()
    supplier["supplier_otif"] = supplier.otif_count/supplier.deliveries
    supplier["late_delivery_rate"] = supplier.late_count/supplier.deliveries
    supplier["fill_rate"] = supplier.delivered_quantity/supplier.ordered_quantity
    supplier = t["dim_supplier"].merge(supplier, on="supplier_id", how="left")
    shipment = t["fact_shipment"]
    logistics = shipment.groupby(["carrier_id", "facility_id", "route"]).agg(shipments=("shipment_id", "count"), otif_count=("otif", "sum"), late_count=("delay_days", lambda x: int((x > 0).sum())), average_delivery_delay=("delay_days", "mean"), ordered_quantity=("ordered_quantity", "sum"), delivered_quantity=("delivered_quantity", "sum")).reset_index()
    logistics["logistics_otif"] = logistics.otif_count/logistics.shipments
    logistics["late_shipment_rate"] = logistics.late_count/logistics.shipments
    logistics["fill_rate"] = logistics.delivered_quantity/logistics.ordered_quantity
    facility_rows = []
    production = t["fact_production"]
    for row in t["dim_facility"].itertuples(index=False):
        fid = row.facility_id
        ss = sales[sales.facility_id == fid]
        pp = production[production.facility_id == fid]
        hh = health[health.facility_id == fid]
        last_prod = pp[pp.production_date == as_of]
        facility_rows.append({"facility_id": fid, "facility_name": row.facility_name, "production_quantity": int(pp.produced_quantity.sum()), "planned_quantity": int(pp.planned_quantity.sum()), "production_attainment": ratio(pp.produced_quantity.sum(), pp.planned_quantity.sum()), "demand_quantity": int(ss.ordered_quantity.sum()), "inventory_quantity": int(hh.on_hand_quantity.sum()), "latest_production": int(last_prod.produced_quantity.sum()), "latest_planned": int(last_prod.planned_quantity.sum()), "latest_production_attainment": ratio(last_prod.produced_quantity.sum(), last_prod.planned_quantity.sum()), **order_summary(ss, as_of)})
    executive = {"as_of": str(as_of.date()), "history_days": days, "total_demand": int(sales.ordered_quantity.sum()), "inventory_quantity": int(health.on_hand_quantity.sum()), "inventory_value": float(health.inventory_value.sum()), "average_inventory_quantity": float(health.average_inventory.sum()), "synthetic_cogs_proxy": float(health.synthetic_cogs_proxy.sum()), "inventory_turnover": ratio(health.synthetic_cogs_proxy.sum(), health.average_inventory_value.sum()), "days_of_inventory": ratio(health.average_inventory.sum(), sales.ordered_quantity.sum()/days), "supplier_otif": float(t["fact_supplier_delivery"].otif.mean()), "logistics_otif": float(shipment.otif.mean()), "late_shipment_rate": float((shipment.delay_days > 0).mean()), "average_delivery_delay": float(shipment.delay_days.mean()), "shipment_count": len(shipment), "stockout_count": int(health.stockout_count.sum()), "excess_inventory_pairs": int(health.excess_inventory.sum()), **order_summary(sales, as_of)}
    return {"agg_demand": demand, "agg_inventory": health, "agg_supplier": supplier, "agg_logistics": logistics, "agg_facility": pd.DataFrame(facility_rows), "executive_kpis": pd.DataFrame([executive])}
