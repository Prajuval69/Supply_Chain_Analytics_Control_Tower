# KPI Definitions

Quantities are synthetic finished-unit equivalents; standard cost is fictional INR/unit. As-of is the latest cleaned inventory snapshot, independent of server time. History starts on the first month and ends at as-of inclusive. Zero denominators yield null/blank.

## Demand

| Metric | Exact formula |
|---|---|
| Total demand | Sum ordered_quantity across eligible order lines |
| Monthly demand | Sum ordered_quantity by order month × product × facility |
| Monthly fulfilled/backlog | Sums of the respective line quantities at that grain |
| Growth | (current − previous month demand) / previous; null for zero/missing previous |
| Volatility | Sample monthly standard deviation / monthly mean; null for zero mean |
| Product/facility demand | Sum monthly quantities after dimension filtering |

Dense monthly grids include true zero-demand months. Stored pair volatility repeats the **full-history** coefficient on each month and must not be summed. HIGH_DEMAND_VOLATILITY evaluates product-level monthly demand across facilities, not sparse pair-level demand.

## Inventory

| Metric | Exact formula / interpretation |
|---|---|
| Quantity | Latest snapshot on_hand_quantity; never sum snapshots across dates |
| Average inventory | Mean month-end quantity per product/facility; sum pair means for executive total |
| Current value | Current quantity × standard_cost |
| Average value | Average quantity × standard_cost |
| Synthetic COGS proxy | Sum fulfilled_quantity × standard_cost across history |
| Turnover | Synthetic COGS proxy / average inventory **value**; full-period turns, not annualized |
| Average daily demand | Historical ordered quantity / inclusive history calendar days |
| Days of inventory | Average inventory / average daily demand |
| Current days of inventory | Latest inventory / average daily demand |
| Stockout count | Number of month-end product/facility snapshots with on-hand ≤ threshold; not intramonth days |
| Current excess flag | Current days > excess_days; also positive stock with zero demand |
| Projected ending | Opening + known expected receipts − allocated forecast demand |
| Projected stockout | Ending ≤ configured stockout threshold |
| Crossing date | ceil((opening + receipts − threshold) / monthly forecast × days in month), bounded to month; start date if already ≤ threshold |
| Projected excess | Positive ending / (monthly forecast / month days) > excess_days; positive stock with zero forecast also qualifies |
| Replenishment | If risk: max(0, ceil(month forecast + threshold − ending)); otherwise 0 |
| Risk pairs | Distinct product/facility combinations with any projected stockout within horizon |

Replenishment clears modeled deficit and adds one month-equivalent demand buffer. Crossing date assumes start-of-month receipts and uniform consumption. Negative projections mean uncovered requirement, not physical negative inventory; deficits carry forward.

## Suppliers

Eligibility is observed deliveries, including partial deliveries. Open POs are excluded from delivery ratios and checked separately for overdue exceptions. Received partial POs are closed in the simulation.

| Metric | Formula |
|---|---|
| Supplier OTIF | Count(delivery_date ≤ expected_date **and** delivered_quantity ≥ full PO ordered_quantity) / observed deliveries |
| Average lead time | Mean(delivery_date − order_date), days |
| Lead-time variance | Sample variance of lead days (ddof=1); null for one observation |
| Late rate | Count(delivery_date > expected_date) / observed deliveries |
| Fill rate | Sum delivered / sum ordered for delivered POs, quantity weighted |
| Delay | max(0, delivery_date − expected_date), days |

Executive OTIF uses total successes / total deliveries, never an unweighted mean of supplier rates.

## Orders

| Metric | Formula |
|---|---|
| Order count | Distinct order_id |
| Fulfilled orders | Count orders with sum fulfilled ≥ sum ordered across all lines |
| Open orders | Total − fulfilled |
| Overdue orders | Open orders whose required_date < as-of; equality is not overdue |
| Fulfillment rate | Fulfilled orders / all eligible orders |
| Backlog | Sum(ordered − fulfilled) across lines |
| Fill rate | Sum fulfilled / sum ordered |

Every order belongs to one facility. Historical incomplete orders remain backlog; later supply does not backfill them. Product-filtered order measures require care: whole-order status is computed from all lines, whereas filtered fill rate concerns selected products.

## Logistics

Observed shipment grain is one shipped line. Zero-fulfilled lines have no shipment and appear in backlog. OTIF therefore is an observed-shipment KPI, not full-order delivery performance.

| Metric | Formula |
|---|---|
| Shipments | Count shipment_id |
| OTIF | Count(actual_delivery_date ≤ promised_date **and** delivered ≥ full ordered line quantity) / shipments |
| Average delay | Mean(max(0, actual_delivery_date − promised_date)); includes zero on-time delays |
| Late rate | Count(actual_delivery_date > promised_date) / shipments |
| Fill rate | Sum delivered / sum ordered quantity for shipped lines |
| Carrier/route | Same metrics by carrier × facility × route, combined using counts/quantity weights |

## Facility

Production = sum produced; planned = sum planned; attainment = produced/planned. Latest attainment uses the final month. Demand, latest inventory, distinct-order fulfillment and backlog follow the above definitions after facility filtering. `exceptions` counts all statuses linked to the facility; API additionally reports live Open/Investigating counts. Supplier-only/product-only exceptions receive no invented facility.

## Forecasting and thresholds

MAE = mean absolute error, units. RMSE = square root of mean squared error, units. MAPE = mean(|actual − prediction| / |actual|) × 100 over nonzero actuals; preserve eligible count. Pooled scores operate on product/target forecast errors. Validation selects per product by MAE; untouched test reports independent performance.

Defaults in `config/settings.json`: stockout ≤ 0 units; excess > 90 days; supplier OTIF < 75%; product CV > 0.45; production attainment < 90%; supplier/shipment delays > 3 days; overdue line backlog > 30 units. They are demonstration policies, not calibrated service targets.
