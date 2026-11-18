# Project Walkthrough

## Business story

PackRight needs to connect customer demand, production, inventory, suppliers and deliveries into a control tower. The project demonstrates both engineering and business reasoning using synthetic data. It is not an internal Greif system.

## Reproduce and trace

1. Install the locked local environment using README.md, then run `python -m src.pipeline.run`.
2. Inspect `data/reference/simulation.json` and `defect_manifest.json`. Each source CSV is under its ERP/MES/WMS/supplier/logistics folder.
3. Compare raw and staging files, then inspect `data_quality.json` and `quarantine_*.csv`. Six deliberately invalid/duplicate rows are excluded; product category case is repaired.
4. Open `database/schema.sql`. Identify sales line primary key, inventory balance check, shipment line reference and supplier PO reference. Use `database/analytical_queries.sql` to analyze SQL directly.
5. Trace an order line through `fact_sales_order`, its shipment and the month/product/facility demand aggregate. Compare quantity fill rate with distinct-order fulfillment: an almost-filled order is still incomplete.
6. Trace a month-end inventory record to its opening balance, production, supplier receipts and fulfilled demand. Validate continuity into the next month.
7. Inspect candidate forecast validation, selected flags and untouched final holdout. Future forecasts are fitted only after evaluation, and future actuals are null.
8. Trace product forecast allocation to facilities and carry the inventory balance through three horizons. Known receipts only and no future production make this a transparent shortage scenario.
9. Inspect exceptions' metric, threshold and action. PATCH an exception through Swagger and show that a rerun preserves the status for stable IDs.
10. Import `outputs/powerbi` using POWER_BI_GUIDE.md. Build the specified six pages; no PBIX is claimed without Desktop.
11. Run tests, independent audit and live HTTP smoke. BUILD_VERIFICATION.md reports actual results and limitations.

## Explain important distinctions

Order count is not line count. OTIF needs both timing and quantity. An average of supplier percentages can mislead; count successes and eligible deliveries. Inventory turnover uses currency on both sides and an explicit synthetic cost proxy. Summing month-end inventory across time overstates current stock. Forecast model selection metrics differ from independent test performance. A modeled deficit is not negative physical inventory. Observed delay/shortage is not proof of root cause.

## Suggested demo

Show executive summary, facility backlog ranking, a low-OTIF supplier, the stockout projection and the corresponding exception. Ask the credential-free assistant “Why is OTIF low?” to display observed failure counts. End with the real test/audit receipts and discuss the high MAPE, monthly-ledger assumption and conservative receipt-only projection.

Business actions are hypothetical: supplier recovery conversations, schedule review, inventory transfers and order prioritization. The project recommends them; it does not execute them. Improvements would include daily stock ledgers, backlog allocation, scheduled production receipts, lead-time uncertainty, workflow audit and incremental ingestion.
