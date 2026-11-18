# Testing and Verification

Run `python -m pytest --junitxml=outputs/reports/pytest.xml`. Tests generate an isolated 18-month dataset in pytest temporary storage, execute the actual pipeline, load the real SQLite schema and call the API. They do not modify the full-size portfolio dataset. Actual latest results are in BUILD_VERIFICATION.md and pytest XML.

| Area | Evidence covered |
|---|---|
| Generation | Same-seed byte reproducibility, five sources, history, controlled defects, demand/production correlation, weaker facility, qualified suppliers |
| Cleaning | Required schema, missing keys, invalid references/dates/sequences, duplicates, negatives, standardized categories |
| Integrity | Inventory ledger and continuity, independent receipt/consumption reconciliation, PO lineage, SQL checks and foreign keys |
| KPIs | Hand-calculated weighted fill/turnover and distinct orders, independent SQL demand/OTIF/turnover, facility reconciliation, zero denominators |
| Forecasts | Known MAE/RMSE/MAPE, zero actuals, invalid inputs, baseline, seasonal/trend fit, no future leakage, independent holdout, validation-only selection |
| Inventory/exception rules | Projection balance/carry, allocation totals, crossing-date boundaries, flags, recommendations, all eight types, evidence and thresholds |
| API/assistant | All routes, pagination/filtering, errors, empty results, injection values, missing warehouse, status persistence/live count, seven intents, offline provider fallback |
| Full pipeline | Repeat run/export hashes, status preservation and warehouse row/export consistency |

Parameterizations vary meaningful business/error boundaries. Assertions verify actual data behavior, not placeholder return values. The test suite is intentionally larger than the required minimum of 30.

`python -m scripts.audit_outputs` independently checks the **default full-size execution** against minimum record counts and 30-month expectations, then reconciles source-derived flows, rates, turnover, forecasts, behavioral signals and exported hashes. This is separate from small-fixture tests. Its minimum-count audit is intentionally for the default portfolio configuration, not a scaled custom root.

Start uvicorn, then `python -m scripts.smoke_api` for a real HTTP receipt (all required GETs, PATCH persistence/restoration, assistant and expected 404/422). TestClient checks alone are not represented as live server execution.

`python -m pip check` checks dependency consistency. `python -m compileall -q src scripts tests` checks imports/compilation. `python -m scripts.document_results` regenerates evidence documentation only after pipeline, test, audit and HTTP receipts pass. Stop the API before rerunning/replacing the warehouse on Windows if a client holds a connection.

Known non-failing warning: installed Starlette's TestClient references AnyIO's deprecated BlockingPortal alias. It does not affect these passed tests; pinning/modernizing framework dependencies is future maintenance. No warnings are hidden. Power BI DAX execution and visual acceptance remain unverified without Desktop. No live external LLM accuracy claim is made.
