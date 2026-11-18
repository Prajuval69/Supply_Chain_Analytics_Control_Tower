# Data Dictionary

Generated from the actual populated SQLite schema. All records are fictional and synthetic.

IDs are positive simulation keys. Dates are ISO YYYY-MM-DD. Quantities are finished-unit equivalents; monetary values are fictional INR. Rates are 0–1 except MAPE (0–100). SQL primary keys, references and check constraints are in `database/schema.sql`. Raw/source keys and contracts are in `src/data/contracts.py`; cleaned data retains the source fields before curated enrichments.

Customer fields: customer_id/name, region, segment. Product: product_id/name, category, unit, standard_cost, lead_time_days, seasonal. Supplier: supplier_id/name, region, default lead, tier. Facility: facility_id/name, city, capacity. Sales order source stores header dates/customer/facility/status separately from order_lines with line_id, order_id, product_id, ordered/fulfilled quantity; the warehouse joins them without changing line grain. Source production, inventory, PO, delivery and shipment fields appear in corresponding facts below. All label strings are fictional.

Null ratios mean undefined denominator/insufficient samples. Exception entity IDs may be null when not applicable. Future actuals and no-risk crossing dates are null. Physical source records with required nulls are quarantined. Analytical snapshots with no date key do not support arbitrary historical-date slicing.

## dim_date

One calendar day; historical and three future months.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| date_id | INTEGER | No | Calendar key YYYYMMDD |
| date | TEXT | No | ISO calendar date |
| year | INTEGER | No | Calendar year |
| month | INTEGER | No | Month start date in analytics; month number in dim_date |
| quarter | INTEGER | No | Calendar quarter 1–4 |
| month_start | TEXT | No | First day of calendar month |

## dim_customer

One fictional customer.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| customer_id | INTEGER | No | Stable customer key; see SQL references |
| customer_name | TEXT | No | Fictional customer display label |
| region | TEXT | No | Synthetic customer/supplier geographic region |
| customer_segment | TEXT | No | Enterprise, SME or Distributor |

## dim_product

One finished-unit SKU.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| product_id | INTEGER | No | Stable product key; see SQL references |
| product_name | TEXT | No | Fictional product display label |
| category | TEXT | No | Canonical packaging category |
| unit | TEXT | No | Finished-unit unit of measure |
| standard_cost | REAL | No | Synthetic INR/unit cost, not accounting COGS |
| lead_time_days | INTEGER | No | Product nominal lead days or observed delivery lead days, depending on table |
| seasonal | INTEGER | No | 1 if generator applies annual demand modulation, otherwise 0 |

## dim_supplier

One fictional supplier.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| supplier_id | INTEGER | No | Stable supplier key; see SQL references |
| supplier_name | TEXT | No | Fictional supplier display label |
| region | TEXT | No | Synthetic customer/supplier geographic region |
| default_lead_time_days | INTEGER | No | Supplier nominal lead days |
| supplier_tier | TEXT | No | Preferred or Watch (systematically poorer simulation behavior) |

## dim_facility

One facility.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| facility_name | TEXT | No | Fictional facility display label |
| city | TEXT | No | Facility city |
| capacity | INTEGER | No | Illustrative monthly facility units; metadata, not a constrained scheduler |

## dim_carrier

One carrier.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| carrier_id | INTEGER | No | Stable carrier key; see SQL references |
| carrier_name | TEXT | No | Fictional carrier display label |
| mode | TEXT | No | Transport mode, Road |

## bridge_supplier_product

One qualified supplier/SKU combination.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| supplier_product_id | INTEGER | No | Stable supplier product key; see SQL references |
| supplier_id | INTEGER | No | Stable supplier key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |

## fact_sales_order

One order line (two per header in default generator).

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| line_id | INTEGER | No | Stable line key; see SQL references |
| order_id | INTEGER | No | Stable order key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |
| ordered_quantity | INTEGER | No | Full requested customer/PO quantity |
| fulfilled_quantity | INTEGER | No | Customer units supplied, capped by stock and requested quantity |
| order_date | TEXT | No | Date demand/PO was placed |
| customer_id | INTEGER | No | Stable customer key; see SQL references |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| required_date | TEXT | No | Customer required date |
| status | TEXT | No | Order Open/Fulfilled; PO Open/Received; production Complete; exception workflow Open/Investigating/Resolved/Accepted |
| backlog_quantity | INTEGER | No | Ordered minus fulfilled units |

## fact_production

One product/facility/month production record.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| production_id | INTEGER | No | Stable production key; see SQL references |
| production_date | TEXT | No | Monthly production accounting date |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |
| planned_quantity | INTEGER | No | Demand-driven planned production units |
| produced_quantity | INTEGER | No | Actual simulated production units |
| status | TEXT | No | Order Open/Fulfilled; PO Open/Received; production Complete; exception workflow Open/Investigating/Resolved/Accepted |

## fact_inventory

One product/facility/month-end physical ledger.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| inventory_id | INTEGER | No | Stable inventory key; see SQL references |
| snapshot_date | TEXT | No | Month-end inventory measurement date |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |
| opening_quantity | INTEGER | No | Prior month closing physical quantity (initial seeded balance in first month) |
| production_quantity | INTEGER | No | Monthly produced units credited to inventory |
| receipt_quantity | INTEGER | No | Observed supplier units received that month |
| consumed_quantity | INTEGER | No | Fulfilled sales units debited that month |
| on_hand_quantity | INTEGER | No | Nonnegative month-end physical units |

## fact_purchase_order

One procurement order for one SKU and facility.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| po_id | INTEGER | No | Stable po key; see SQL references |
| supplier_id | INTEGER | No | Stable supplier key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| order_date | TEXT | No | Date demand/PO was placed |
| expected_date | TEXT | No | PO expected receipt date |
| ordered_quantity | INTEGER | No | Full requested customer/PO quantity |
| status | TEXT | No | Order Open/Fulfilled; PO Open/Received; production Complete; exception workflow Open/Investigating/Resolved/Accepted |

## fact_supplier_delivery

One observed delivery per PO, including partial closed POs.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| delivery_id | INTEGER | No | Stable delivery key; see SQL references |
| po_id | INTEGER | No | Stable po key; see SQL references |
| supplier_id | INTEGER | No | Stable supplier key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| delivery_date | TEXT | No | Observed supplier delivery date |
| delivered_quantity | INTEGER | No | Observed delivered units |
| order_date | TEXT | No | Date demand/PO was placed |
| expected_date | TEXT | No | PO expected receipt date |
| ordered_quantity | INTEGER | No | Full requested customer/PO quantity |
| lead_time_days | INTEGER | No | Product nominal lead days or observed delivery lead days, depending on table |
| delay_days | INTEGER | No | Nonnegative actual minus promised/expected days |
| on_time | INTEGER | No | 1 when actual delivery date ≤ promised/expected date |
| in_full | INTEGER | No | 1 when delivered ≥ full ordered quantity |
| otif | INTEGER | No | on_time AND in_full, stored as 0/1 |

## fact_shipment

One shipment per positive-fulfilled order line.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| shipment_id | INTEGER | No | Stable shipment key; see SQL references |
| line_id | INTEGER | No | Stable line key; see SQL references |
| order_id | INTEGER | No | Stable order key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| carrier_id | INTEGER | No | Stable carrier key; see SQL references |
| ship_date | TEXT | No | Shipment departure date |
| promised_date | TEXT | No | Promised customer delivery date |
| actual_delivery_date | TEXT | No | Observed customer delivery date |
| shipped_quantity | INTEGER | No | Units dispatched |
| delivered_quantity | INTEGER | No | Observed delivered units |
| route | TEXT | No | Origin facility city to synthetic customer region |
| ordered_quantity | INTEGER | No | Full requested customer/PO quantity |
| delay_days | INTEGER | No | Nonnegative actual minus promised/expected days |
| on_time | INTEGER | No | 1 when actual delivery date ≤ promised/expected date |
| in_full | INTEGER | No | 1 when delivered ≥ full ordered quantity |
| otif | INTEGER | No | on_time AND in_full, stored as 0/1 |

## agg_demand

One dense month/product/facility demand observation.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| month | TEXT | No | Month start date in analytics; month number in dim_date |
| product_id | INTEGER | No | Stable product key; see SQL references |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| demand_quantity | INTEGER | Yes | Ordered units at aggregate grain |
| fulfilled_quantity | INTEGER | Yes | Customer units supplied, capped by stock and requested quantity |
| backlog_quantity | INTEGER | Yes | Ordered minus fulfilled units |
| previous_demand | REAL | Yes | Dense preceding-month demand; null in first month |
| demand_growth | REAL | Yes | (current-previous)/previous, null for zero/missing previous |
| demand_volatility | REAL | Yes | Sample monthly CV for product/facility across full history |

## agg_inventory

One latest product/facility health snapshot with full-history statistics.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| inventory_id | INTEGER | Yes | Stable inventory key; see SQL references |
| snapshot_date | TEXT | Yes | Month-end inventory measurement date |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| product_id | INTEGER | No | Stable product key; see SQL references |
| opening_quantity | INTEGER | Yes | Prior month closing physical quantity (initial seeded balance in first month) |
| production_quantity | INTEGER | Yes | Monthly produced units credited to inventory |
| receipt_quantity | INTEGER | Yes | Observed supplier units received that month |
| consumed_quantity | INTEGER | Yes | Fulfilled sales units debited that month |
| on_hand_quantity | INTEGER | Yes | Nonnegative month-end physical units |
| average_inventory | REAL | Yes | Mean physical month-end quantity |
| stockout_count | INTEGER | Yes | Count month-end snapshots at/below threshold |
| demand_quantity | REAL | Yes | Ordered units at aggregate grain |
| fulfilled_quantity | REAL | Yes | Customer units supplied, capped by stock and requested quantity |
| standard_cost | REAL | Yes | Synthetic INR/unit cost, not accounting COGS |
| average_daily_demand | REAL | Yes | Historical demand divided by inclusive history days |
| days_of_inventory | REAL | Yes | Historical average stock coverage in health, projected month coverage in projections |
| current_days_of_inventory | REAL | Yes | Latest stock / historical average daily demand |
| inventory_value | REAL | Yes | Latest units × synthetic standard cost |
| average_inventory_value | REAL | Yes | Mean physical units × synthetic standard cost |
| synthetic_cogs_proxy | REAL | Yes | Fulfilled units × standard cost across history |
| inventory_turnover | REAL | Yes | Full-history COGS proxy / average inventory value, not annualized |
| excess_inventory | INTEGER | Yes | Current health excess flag, 0/1 |

## agg_supplier

One supplier, observed-delivery full-history statistics.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| supplier_id | INTEGER | No | Stable supplier key; see SQL references |
| supplier_name | TEXT | Yes | Fictional supplier display label |
| region | TEXT | Yes | Synthetic customer/supplier geographic region |
| default_lead_time_days | INTEGER | Yes | Supplier nominal lead days |
| supplier_tier | TEXT | Yes | Preferred or Watch (systematically poorer simulation behavior) |
| deliveries | INTEGER | Yes | Observed supplier delivery count |
| otif_count | INTEGER | Yes | Number of deliveries/shipments satisfying both criteria |
| on_time_count | INTEGER | Yes | Number of on-time deliveries |
| average_lead_time | REAL | Yes | Mean observed supplier lead days |
| lead_time_variance | REAL | Yes | Sample lead-time variance in days squared |
| late_count | INTEGER | Yes | Number of positive-delay observed deliveries/shipments |
| delivered_quantity | INTEGER | Yes | Observed delivered units |
| ordered_quantity | INTEGER | Yes | Full requested customer/PO quantity |
| supplier_otif | REAL | Yes | Supplier count-weighted OTIF ratio |
| late_delivery_rate | REAL | Yes | Late supplier deliveries / observed deliveries |
| fill_rate | REAL | Yes | Quantity-weighted fulfilled/delivered fraction |

## agg_logistics

One carrier/facility/route full-history aggregate.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| carrier_id | INTEGER | No | Stable carrier key; see SQL references |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| route | TEXT | No | Origin facility city to synthetic customer region |
| shipments | INTEGER | Yes | Shipment count at aggregate grain |
| otif_count | INTEGER | Yes | Number of deliveries/shipments satisfying both criteria |
| late_count | INTEGER | Yes | Number of positive-delay observed deliveries/shipments |
| average_delivery_delay | REAL | Yes | Mean nonnegative delay including on-time zero days |
| ordered_quantity | INTEGER | Yes | Full requested customer/PO quantity |
| delivered_quantity | INTEGER | Yes | Observed delivered units |
| logistics_otif | REAL | Yes | Count-weighted shipment OTIF ratio |
| late_shipment_rate | REAL | Yes | Late shipments / observed shipments |
| fill_rate | REAL | Yes | Quantity-weighted fulfilled/delivered fraction |

## agg_facility

One facility, full-history performance and current inventory.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| facility_name | TEXT | Yes | Fictional facility display label |
| production_quantity | INTEGER | Yes | Monthly produced units credited to inventory |
| planned_quantity | INTEGER | Yes | Demand-driven planned production units |
| production_attainment | REAL | Yes | Full-history produced / planned |
| demand_quantity | INTEGER | Yes | Ordered units at aggregate grain |
| inventory_quantity | INTEGER | Yes | Total latest month-end physical units for executive/facility snapshot |
| latest_production | INTEGER | Yes | Latest month's produced units |
| latest_planned | INTEGER | Yes | Latest month's planned units |
| latest_production_attainment | REAL | Yes | Latest produced / planned |
| order_count | INTEGER | Yes | Distinct customer order count |
| fulfilled_orders | INTEGER | Yes | Orders whose complete quantity was supplied |
| open_orders | INTEGER | Yes | Distinct orders still incomplete |
| overdue_orders | INTEGER | Yes | Incomplete orders required before synthetic as-of |
| fulfillment_rate | REAL | Yes | Fulfilled orders / eligible orders |
| backlog_quantity | INTEGER | Yes | Ordered minus fulfilled units |
| fill_rate | REAL | Yes | Quantity-weighted fulfilled/delivered fraction |
| exceptions | INTEGER | Yes | All detected exceptions linked to facility |

## executive_kpis

One global as-of snapshot.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| as_of | TEXT | No | Maximum cleaned inventory date |
| history_days | INTEGER | Yes | Inclusive calendar days from first history month to as-of |
| total_demand | INTEGER | Yes | Total historical ordered units |
| inventory_quantity | INTEGER | Yes | Total latest month-end physical units for executive/facility snapshot |
| inventory_value | REAL | Yes | Latest units × synthetic standard cost |
| average_inventory_quantity | REAL | Yes | Sum of per-pair mean month-end units |
| synthetic_cogs_proxy | REAL | Yes | Fulfilled units × standard cost across history |
| inventory_turnover | REAL | Yes | Full-history COGS proxy / average inventory value, not annualized |
| days_of_inventory | REAL | Yes | Historical average stock coverage in health, projected month coverage in projections |
| supplier_otif | REAL | Yes | Supplier count-weighted OTIF ratio |
| logistics_otif | REAL | Yes | Count-weighted shipment OTIF ratio |
| late_shipment_rate | REAL | Yes | Late shipments / observed shipments |
| average_delivery_delay | REAL | Yes | Mean nonnegative delay including on-time zero days |
| shipment_count | INTEGER | Yes | Total observed shipments |
| stockout_count | INTEGER | Yes | Count month-end snapshots at/below threshold |
| excess_inventory_pairs | INTEGER | Yes | Current excess product/facility count |
| order_count | INTEGER | Yes | Distinct customer order count |
| fulfilled_orders | INTEGER | Yes | Orders whose complete quantity was supplied |
| open_orders | INTEGER | Yes | Distinct orders still incomplete |
| overdue_orders | INTEGER | Yes | Incomplete orders required before synthetic as-of |
| fulfillment_rate | REAL | Yes | Fulfilled orders / eligible orders |
| backlog_quantity | INTEGER | Yes | Ordered minus fulfilled units |
| fill_rate | REAL | Yes | Quantity-weighted fulfilled/delivered fraction |
| stockout_risk_pairs | INTEGER | Yes | Distinct pairs with projected risk in horizon |
| open_exceptions | INTEGER | Yes | Open/Investigating exception count at export time |

## forecast_demand

One product/future horizon; actual unknown.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| product_id | INTEGER | No | Stable product key; see SQL references |
| train_end | TEXT | Yes | Last training month, excluding prediction targets |
| forecast_date | TEXT | Yes | Target month start |
| horizon | INTEGER | No | Forecast step 1–3 |
| prediction | REAL | Yes | Nonnegative product demand point estimate |
| actual | TEXT | Yes | Observed validation/test demand; null for future |
| model_name | TEXT | Yes | moving_average_3 or trend_seasonal_regression |
| mae | REAL | Yes | Product/candidate validation mean absolute error, units |
| rmse | REAL | Yes | Validation root mean squared error, units |
| mape | REAL | Yes | Validation percent absolute error over nonzero actuals |
| mape_eligible_count | INTEGER | Yes | Count nonzero actual validation targets |

## forecast_validation

One product/candidate/origin/horizon chronological validation prediction.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| product_id | INTEGER | No | Stable product key; see SQL references |
| train_end | TEXT | No | Last training month, excluding prediction targets |
| forecast_date | TEXT | Yes | Target month start |
| horizon | INTEGER | No | Forecast step 1–3 |
| prediction | REAL | Yes | Nonnegative product demand point estimate |
| actual | REAL | Yes | Observed validation/test demand; null for future |
| model_name | TEXT | No | moving_average_3 or trend_seasonal_regression |

## forecast_model_metrics

One product/candidate validation metric record.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| product_id | INTEGER | No | Stable product key; see SQL references |
| model_name | TEXT | No | moving_average_3 or trend_seasonal_regression |
| mae | REAL | Yes | Product/candidate validation mean absolute error, units |
| rmse | REAL | Yes | Validation root mean squared error, units |
| mape | REAL | Yes | Validation percent absolute error over nonzero actuals |
| mape_eligible_count | INTEGER | Yes | Count nonzero actual validation targets |
| selected | INTEGER | Yes | 1 if candidate chosen by validation MAE |

## forecast_test

One product/horizon final untouched test prediction.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| product_id | INTEGER | No | Stable product key; see SQL references |
| train_end | TEXT | Yes | Last training month, excluding prediction targets |
| forecast_date | TEXT | Yes | Target month start |
| horizon | INTEGER | No | Forecast step 1–3 |
| prediction | REAL | Yes | Nonnegative product demand point estimate |
| actual | REAL | Yes | Observed validation/test demand; null for future |
| model_name | TEXT | Yes | moving_average_3 or trend_seasonal_regression |

## projected_inventory

One product/facility/future horizon inventory scenario.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| product_id | INTEGER | No | Stable product key; see SQL references |
| facility_id | INTEGER | No | Stable facility key; see SQL references |
| forecast_date | TEXT | Yes | Target month start |
| horizon | INTEGER | No | Forecast step 1–3 |
| opening_inventory | REAL | Yes | Latest physical stock for horizon 1, prior scenario ending thereafter |
| expected_receipts | REAL | Yes | Known open PO units assigned to forecast month |
| forecast_demand | REAL | Yes | Product point forecast allocated by recent facility share |
| projected_ending_inventory | REAL | Yes | Opening + receipts - demand; negative represents deficit |
| stockout_flag | INTEGER | Yes | 1 when ending ≤ configured threshold |
| stockout_date | TEXT | Yes | Estimated uniform-consumption crossing date; null if no crossing |
| days_of_inventory | REAL | Yes | Historical average stock coverage in health, projected month coverage in projections |
| excess_inventory_flag | INTEGER | Yes | 1 for projected excess coverage |
| replenishment_quantity | INTEGER | Yes | Deficit plus one-month buffer when risk flagged |
| recommendation | TEXT | Yes | Deterministic planner action for projection |

## supply_chain_exception

One deterministic type/business-reference exception.

| Field | SQLite type | Nullable | Meaning |
|---|---|---|---|
| exception_id | TEXT | No | Stable EX- plus truncated type/reference SHA-256 |
| type | TEXT | Yes | One of eight rule types |
| severity | TEXT | Yes | Critical, High, Medium or Low |
| facility_id | INTEGER | Yes | Stable facility key; see SQL references |
| product_id | INTEGER | Yes | Stable product key; see SQL references |
| supplier_id | INTEGER | Yes | Stable supplier key; see SQL references |
| reference | TEXT | Yes | Business reference (line, shipment, delivery, PO or product/facility) |
| detected_date | TEXT | Yes | Synthetic as-of rule detection date |
| metric | TEXT | Yes | Name of compared metric; determines units |
| threshold | REAL | Yes | Configured/computed trigger boundary |
| actual_value | REAL | Yes | Observed/projected metric compared with threshold |
| expected_value | REAL | Yes | Rule target |
| status | TEXT | Yes | Order Open/Fulfilled; PO Open/Received; production Complete; exception workflow Open/Investigating/Resolved/Accepted |
| recommended_action | TEXT | Yes | Explainable deterministic rule recommendation |

