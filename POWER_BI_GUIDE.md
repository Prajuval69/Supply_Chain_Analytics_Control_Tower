# Power BI Control Tower: Complete Six-Page Specification

All report pages must display **PackRight Manufacturing — synthetic portfolio demonstration**, the synthetic as-of date and current filter context. No real company data, rendered dashboard screenshot or PBIX is claimed. Power BI Desktop was not found in checked locations; these import assets and build instructions are the supported deliverable.

## Import and model

Run the pipeline first. In Desktop create a text parameter `DataFolder` pointing to this checkout's `outputs/powerbi`. Paste `config/import_csv.pq` into a blank query named `fnPackRightCsv`; create each table with `fnPackRightCsv(DataFolder,"<filename without .csv>")`. This loader converts dates, numeric keys/metrics and blanks to null. Review data types rather than accepting automatic inference. CSVs are UTF-8, quantities numeric, IDs integer, dates ISO, monetary values fictional INR, rates decimals 0–1 and MAPE percent 0–100.

Required reporting files: executive_kpis, demand_trends, inventory_health, supplier_scorecard, logistics_performance, facility_performance, forecast_demand, projected_inventory, supply_chain_exceptions. Additional dimension/fact CSVs enable a complete model and date-sensitive analysis: dim_date/customer/product/supplier/facility/carrier, six fact tables, bridge_supplier_product, forecast_validation/test/model_metrics. Import all facts and dimensions; only import aggregates needed by visuals. Never join fact to fact or auto-create bidirectional relationships.

| One-side dimension | Many-side tables / key | Direction |
|---|---|---|
| dim_product.product_id | Sales, production, inventory, PO, supplier delivery, shipment, demand_trends, inventory_health, forecasts, projections, exceptions, bridge | Single, dimension → table |
| dim_facility.facility_id | All facts; demand_trends, inventory_health, logistics_performance, facility_performance, projected_inventory, exceptions | Single |
| dim_supplier.supplier_id | PO, delivery, supplier_scorecard, exceptions, bridge | Single |
| dim_carrier.carrier_id | Shipment, logistics_performance | Single |
| dim_customer.customer_id | Sales only | Single |
| dim_date.date | Sales order_date; production production_date; inventory snapshot_date; PO order_date; supplier delivery delivery_date; shipment actual_delivery_date | Single |
| dim_date.date | demand_trends.month; forecast tables forecast_date; projected_inventory.forecast_date | Single |

Use ISO `date` relationships (not date_id because the facts expose date fields). Mark dim_date as the date table. Required/promised/expected dates may have **inactive** relationships and explicit USERELATIONSHIP measures or role-playing calendars. Do not activate multiple date relationships per fact. Exception detected_date is fixed as-of; leave it disconnected from the historical date slicer. executive_kpis is a disconnected global snapshot. Aggregate supplier/logistics/facility/inventory_health tables have **no historical date relationship**: their history statistics are snapshots and must be labeled accordingly.

Dimensional filters work only where the relevant key exists. For example product-level forecast has no facility key: use projected_inventory's allocated forecast for facility analysis. Do not filter supplier scorecards by product/facility using a disconnected aggregate; use fact_supplier_delivery measures for those views. All percent totals must recompute numerator/denominator. Do not average precomputed percentages, sum inventory across dates or sum repeated volatility.

Create measures individually from `docs/powerbi_measures.dax`. The measures use file/table names above. Hide technical IDs from general readers, keep them available for drillthrough. Format rates as %, MAPE as decimal with a `%` suffix (already multiplied by 100), cost as INR and quantities as units. Configure measure folders for demand, inventory, suppliers, logistics, forecasting and exceptions. Import `config/powerbi_theme.json`.

## Shared layout and interactions

Use 16:9 canvas with header/as-of/navigation, top KPI row, two main chart panels, lower detailed table and footer definitions. Six page buttons give explicit navigation. Use slate text on a light background, teal for normal operations, amber for Medium/Investigating, red for High/Critical; also show text/icon status so meaning is not color-only. Quantity bars start at zero; rate axes stay 0–100%. Trend forecasts are dashed and visually separated from actuals. Avoid maps without real coordinates.

Global slicers: product category/product and facility where applicable. Historical date slicers apply only to time-sensitive fact/actual views. Future horizon is a separate control. Configure Edit interactions so a historical date range does not silently blank snapshot cards or future forecasts. Every static card must say “as-of snapshot / full history”. Tooltips show numerator, denominator, units, entity, period, definition and source. Detail pages drill through with explicit dimension IDs and a return button. Empty selections display “No matching records”; reset restores All.

## Page 1 — Executive Control Tower

Audience: operations leadership. Questions: Is service deteriorating? Which facility needs intervention? How much inventory and risk are present?

- Top cards: Total Demand, Current Inventory Units/Value, Logistics OTIF, Order Fill Rate, Stockout Risk Pairs, Open Exceptions. Use disconnected executive_kpis for fixed full-history headline cards, or documented fact measures for dimension-filtered cards; do not mix their scopes invisibly.
- Left: monthly demand line from fact_sales_order by dim_date.month_start, ordered units. Right: month-end inventory line from fact_inventory (one stock total per snapshot, never cumulative).
- Lower left: facility matrix with demand, latest inventory, order fulfillment, backlog, production attainment and active exceptions. facility_performance stores full-history values; fact measures support changing date ranges.
- Lower right: exceptions stacked bar by severity/type, with Open/Investigating selected by default. Select a bar to navigate/filter Page 6.
- Controls: facility/category plus labeled historical-date range for trend panels. Forecast/risk cards remain as-of and exclude historical-date interactions. Tooltip explains line-based logistics versus order-based fulfillment.

## Page 2 — Demand & Forecast

Audience: demand planner. Questions: Which SKUs are volatile? What is expected next month? How reliable is the point forecast?

- Cards: period demand, growth, selected-product volatility, Next Month Forecast Units, independent Test MAE/RMSE/MAPE.
- Main: actual monthly ordered demand and future prediction on the same date axis, with actual/forecast labels and the as-of separator. Use product selection; for a facility selection switch future series to Allocated Forecast Units and clearly label allocation assumption.
- Secondary: ranked product demand bars and product/category growth matrix; show null growth for zero prior demand. Volatility is computed on dense periods, not on nonzero transactions alone.
- Lower: selected model table from forecast_model_metrics, both candidate validation MAE/RMSE and selected flag; untouched test actual/predicted line/table from forecast_test. Display evaluation window separately from future horizon.
- Controls: category/product, actual period, forecast horizon 1–3. Facility must not imply that product-level model test scores were independently fitted per facility. Forecast tooltips include train_end, horizon, model, validation scores and “no confidence interval”.

## Page 3 — Inventory Health

Audience: inventory planner. Questions: Where will stock be exhausted? Where is surplus? How much replenishment is recommended?

- Cards: latest units/value, average historical inventory, full-period turnover proxy, days of inventory, stockout/excess risk pairs and replenishment units.
- Main left: product/facility stock matrix from inventory_health with on_hand, current_days_of_inventory, average inventory, cost proxy/turnover and current excess flag.
- Main right: projected ending inventory line by horizon/date for selected product/facility, with 0 threshold line. Use distinct forecast month on the axis so opening/ending are not summed across horizons.
- Lower: stockout table with facility/product, first stockout_date, earliest horizon, expected receipts, forecast consumption and replenishment recommendation; a second surplus bar/table supports rebalancing.
- Controls: facility/category/product, future horizon (single-select, default 1), stockout/excess view. Projected stock and replenishment cards require one horizon; summing successive stock balances or repeated deficit recommendations would mislead. Historical trend uses fact_inventory on a separate date visual. Snapshot statistics remain full-history. Tooltip explicitly states known-PO-only receipts and no future production.

## Page 4 — Supplier Scorecard

Audience: procurement. Questions: Who fails timing and quantity? Is lead time unstable? Which late receipts need recovery?

- Cards: Supplier OTIF, Supplier Fill Rate, average lead time, lead variance and late rate; calculate from delivery facts for selected period/dimensions.
- Main: ranked supplier OTIF horizontal bars (75% policy line); supplier scatter of average lead versus fill rate, sized by delivery count. Label Watch/Preferred tiers without claiming external credit risk.
- Lower: table with supplier, deliveries, numerator counts, quantities, fill, lead mean/variance and late rate; supplier delay exception table with PO/delivery reference and recommended action.
- Controls: supplier/tier, delivery-date range, product/facility for **fact-based** measures. supplier_scorecard is full-history supplier grain and cannot respond to product/facility or dates; either use it only for a clearly static table or replace with fact measures.
- Drillthrough: supplier → underlying deliveries/PO expected vs actual dates and quantities. Open POs are not part of observed-delivery OTIF.

## Page 5 — Logistics

Audience: transport/customer service. Questions: Which carriers/routes delay? How many shipments are partial? What drives arithmetic OTIF failures?

- Cards: shipment count, Logistics OTIF, average nonnegative delay, late rate and Shipment Fill Rate.
- Main: carrier OTIF ranked bars with rate axis; monthly OTIF trend by actual delivery date. Route/facility heatmap includes shipment count to identify small samples.
- Lower: detailed shipments with carrier, route, full ordered line quantity, delivered quantity, promised/actual dates, late flag, in-full flag and OTIF; arithmetic failure decomposition late-only, short-only and both (mutually exclusive).
- Controls: carrier, route, facility/category/product and actual-delivery date. Use fact_shipment for dynamic dates; logistics_performance is full-history carrier/facility/route aggregate.
- Drillthrough: shipment/order/line IDs to evidence and associated Page 6 delay exceptions. Do not conflate observed line shipments with complete customer orders.

## Page 6 — Exceptions

Audience: operational triage. Questions: What needs action first? Who/what is affected? Which policies triggered? Is investigation complete?

- Cards: active exceptions, Critical, High, distinct stockout risk pairs, and selected backlog quantity (label metric scope).
- Main: type × severity stacked bar and facility × severity matrix. Include a separate “No facility: supplier/product-level” group for null entity IDs rather than inventing assignments.
- Lower action table: exception_id, type, severity, status, facility/product/supplier, reference, detected_date, metric, actual_value, threshold, expected_value and recommended_action. Sort Critical → High → Medium → Low, then stable ID. Actual/threshold units depend on metric; display metric-specific unit tooltip.
- Controls: status (default Open/Investigating), severity, type, facility/product/supplier; detected date is the fixed snapshot, not a historical trend. Drillthrough to inventory projection, supplier delivery or shipment based on type.
- Power BI is read-only; status updates use the FastAPI PATCH endpoint. Rerun pipeline and refresh Desktop to display new exported statuses. Do not claim Power BI writeback or external notifications.

## Refresh and acceptance in Desktop

Rerun pipeline, confirm output manifest, then Refresh. Set DataFolder for the local checkout; no machine paths are embedded. Test All → facility 5 → All, product selection/reset, date ranges, future horizon and exception-status filters. Check total/weighted rates against run_summary and query examples; verify latest inventory is not summed across dates. Check every page at normal and narrow viewing size, units/tooltips, empty selections and no chart clipping. Export PDFs/screenshots only from a real rendered report. This Desktop visual/DAX acceptance has not been executed in this environment.
