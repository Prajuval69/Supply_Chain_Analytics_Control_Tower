-- Fictional PackRight, SQLite. Run after the pipeline.
-- Monthly demand and comparable previous-month growth across dense periods.
WITH monthly AS (
 SELECT month, SUM(demand_quantity) demand FROM agg_demand GROUP BY month
), lagged AS (
 SELECT *, LAG(demand) OVER (ORDER BY month) previous_demand FROM monthly
)
SELECT *, 1.0*(demand-previous_demand)/NULLIF(previous_demand,0) growth FROM lagged;

-- Current stock: do not sum snapshots over dates.
SELECT facility_id, SUM(on_hand_quantity) units
FROM fact_inventory
WHERE snapshot_date=(SELECT MAX(snapshot_date) FROM fact_inventory)
GROUP BY facility_id;

-- Supplier OTIF and weighted fill rate, including partial completed deliveries.
SELECT supplier_id, COUNT(*) deliveries,
 AVG(CASE WHEN delivery_date<=expected_date AND delivered_quantity>=ordered_quantity THEN 1.0 ELSE 0.0 END) otif,
 SUM(delivered_quantity)*1.0/NULLIF(SUM(ordered_quantity),0) fill_rate,
 AVG(lead_time_days) lead_days
FROM fact_supplier_delivery GROUP BY supplier_id ORDER BY otif;

-- Carrier performance computed from fact numerators and denominators.
SELECT carrier_id, COUNT(*) shipments, AVG(otif*1.0) otif,
 AVG(delay_days) average_delay,
 AVG(CASE WHEN delay_days>0 THEN 1.0 ELSE 0.0 END) late_rate
FROM fact_shipment GROUP BY carrier_id ORDER BY otif;

-- Distinct-order fulfillment, without confusing two lines with two orders.
WITH orders AS (
 SELECT order_id, facility_id, SUM(ordered_quantity) ordered,
 SUM(fulfilled_quantity) fulfilled, MIN(required_date) required
 FROM fact_sales_order GROUP BY order_id, facility_id
)
SELECT facility_id, COUNT(*) orders,
 SUM(CASE WHEN fulfilled>=ordered THEN 1 ELSE 0 END) fulfilled_orders,
 SUM(ordered-fulfilled) backlog
FROM orders GROUP BY facility_id;

-- Independent inventory monetary turnover proxy, full history, not annualized.
WITH cogs AS (
 SELECT SUM(fulfilled_quantity*standard_cost) value
 FROM fact_sales_order JOIN dim_product USING(product_id)
), snapshots AS (
 SELECT snapshot_date,SUM(on_hand_quantity*standard_cost) value
 FROM fact_inventory JOIN dim_product USING(product_id) GROUP BY snapshot_date
)
SELECT cogs.value/(SELECT AVG(value) FROM snapshots) synthetic_inventory_turnover FROM cogs;

-- Earliest projected risk by product/facility.
SELECT product_id,facility_id,MIN(stockout_date) projected_stockout_date,
 MIN(projected_ending_inventory) worst_requirement
FROM projected_inventory WHERE stockout_flag=1 GROUP BY product_id,facility_id;

-- Exception queue includes evidence, threshold and deterministic action.
SELECT exception_id,type,severity,facility_id,product_id,metric,actual_value,
 threshold,status,recommended_action FROM supply_chain_exception
WHERE status IN ('Open','Investigating')
ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;
