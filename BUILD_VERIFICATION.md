# Build Verification — Actual Execution

Evidence documentation generated 2026-10-03T11:20:51.510672+05:30. No results below are invented. All data is synthetic fictional PackRight data.

Default configuration: seed 42, 30 months starting 2024-04-01; analytical as-of **2026-09-30**. Final full pipeline elapsed 7.071 seconds (local measurement; varies by machine).

## Record counts

| Warehouse table | Records |
|---|---:|
| dim_customer | 500 |
| dim_product | 200 |
| dim_supplier | 100 |
| dim_facility | 5 |
| dim_carrier | 15 |
| bridge_supplier_product | 400 |
| fact_sales_order | 30,000 |
| fact_production | 30,000 |
| fact_inventory | 30,000 |
| fact_purchase_order | 6,600 |
| fact_supplier_delivery | 6,564 |
| fact_shipment | 29,393 |
| dim_date | 1,005 |
| agg_demand | 30,000 |
| agg_inventory | 1,000 |
| agg_supplier | 100 |
| agg_logistics | 375 |
| agg_facility | 5 |
| executive_kpis | 1 |
| forecast_demand | 600 |
| forecast_validation | 2,400 |
| forecast_model_metrics | 400 |
| forecast_test | 600 |
| projected_inventory | 3,000 |
| supply_chain_exception | 2,319 |

Distinct customer orders: 15,000; source header rows include one duplicate and one invalid-date record. Rejected raw rows: 6; remaining category variants standardized. Source rows and cleaned counts are recorded in `run_summary.json` and field profiles in `data_quality.json`.

## Actual KPIs

| Metric | Result |
|---|---:|
| as_of | 2026-09-30 |
| history_days | 913 |
| total_demand | 1097947 |
| inventory_quantity | 103184 |
| inventory_value | 74,305,464.510000 |
| average_inventory_quantity | 64,978.966667 |
| synthetic_cogs_proxy | 735,420,901.780000 |
| inventory_turnover | 15.516044 |
| days_of_inventory | 54.033388 |
| supplier_otif | 0.462675 |
| logistics_otif | 0.296975 |
| late_shipment_rate | 0.467186 |
| average_delivery_delay | 1.938217 |
| shipment_count | 29393 |
| stockout_count | 6405 |
| excess_inventory_pairs | 333 |
| order_count | 15000 |
| fulfilled_orders | 4673 |
| open_orders | 10327 |
| overdue_orders | 10327 |
| fulfillment_rate | 0.311533 |
| backlog_quantity | 142554 |
| fill_rate | 0.870163 |
| stockout_risk_pairs | 626 |
| open_exceptions | 2319 |

Rates above are fractions; cost values are fictional INR. Turnover uses a synthetic COGS proxy over the whole history, not annualized.

## Forecast evidence

Model selection is per product. Both methods evaluated on chronological validation; final three months remain untouched until the selected method is tested. Future actuals are null.

| Selected model | Products |
|---|---:|
| trend_seasonal_regression | 114 |
| moving_average_3 | 86 |

| Evaluation | MAE (units) | RMSE (units) | MAPE (%) | Nonzero actuals |
|---|---:|---:|---:|---:|
| moving_average_3 | 89.847778 | 123.806462 | 75.539151 | 1124 |
| trend_seasonal_regression | 84.688722 | 112.855777 | 71.426660 | 1124 |
| selected_validation | 76.665104 | 105.209148 | 65.868722 | 1124 |
| untouched_test | 88.508579 | 115.805676 | 74.834122 | 554 |

MAPE is high because intermittent low-volume products produce large percentage errors; zero actuals are excluded and counted. Selection results are not a guarantee of future accuracy. No forecast interval was constructed.

## Exceptions

| Type | Count |
|---|---:|
| ORDER_BACKLOG | 636 |
| STOCKOUT_RISK | 626 |
| EXCESS_INVENTORY | 326 |
| PRODUCTION_SHORTFALL | 205 |
| SHIPMENT_DELAY | 203 |
| HIGH_DEMAND_VOLATILITY | 154 |
| LOW_SUPPLIER_OTIF | 100 |
| SUPPLIER_DELAY | 69 |

Severity counts: Critical: 1032, Medium: 512, High: 449, Low: 326.

## Execution and checks

- **97 tests passed**, 0 failures/errors, 0 skipped; actual pytest XML in `outputs/reports/pytest.xml`.
- **58/58 independent full-output checks passed**, receipt dated 2026-10-03T11:20:50.272584+05:30.
- **15 real HTTP smoke checks passed**, against http://127.0.0.1:8000, receipt dated 2026-10-03T11:20:51.056980+05:30. Required GETs, exception GET/PATCH persistence and restoration, assistant POST, expected 404/422 verified.
- SQLite integrity: ok; foreign-key violations: 0.
- Dependency installation completed in `.venv`; `pip check` reported no broken requirements. Python modules compiled successfully.
- Small-fixture pipeline tests verify identical repeat export hashes and persisted exception statuses. Full-size repeat-hash receipt is in `outputs/reports/idempotency.json` when run.
- Source scan found no machine-specific paths or recognizable credential patterns; `.env` and generated database/data/environment files are ignored. This is a scoped recognizable-pattern scan, not a universal secret guarantee.

## Fixes actually made

The first warehouse load exposed a Windows file-lock error because SQLite's transaction context did not close the connection. Explicit closing was added; full pipeline reruns and idempotency checks now succeed. Forecast selection was separated from an untouched final holdout before final verification.

## Artifacts

Power BI CSV files: 25; exact filenames, rows, columns and hashes in `outputs/powerbi/manifest.json`. Nine required datasets plus supporting dimensions/facts/evaluation files exist. Theme, Power Query function and DAX source are authored import assets. Warehouse, forecasts, profiles, quarantines, logs and execution receipts are listed in README.md.

## Honest limitations

Power BI Desktop was not found in checked executable/install locations; no PBIX, screenshot or executed DAX/visual acceptance is claimed. Provider LLM calls were not made; credential-free fallback and mocked provider-failure paths passed. A non-failing Starlette/AnyIO deprecation warning remains. Inventory is month-end accounting, not a daily feasibility simulation; receipts are finished-unit equivalents. Backlog remains cumulative. Future projection assumes known open POs at month start and no future production, and negative balances are uncovered requirements. This is a local demo without authentication or production workflow audit.

## Reproduction

Follow README.md for locked dependencies, full generation/ETL, pytest, output audit, uvicorn and real HTTP smoke. Then run `python -m scripts.document_results` to refresh this receipt and dictionary from actual successful executions. BUILD_CHECKLIST.md records verified requirements; Desktop rendering is explicitly outside the supported environment.
