# Forecasting and Inventory Projection

These point forecasts concern fictional synthetic PackRight demand.

Monthly ordered quantity is aggregated by product across facilities with zero months retained. Default history is April 2024–September 2026 (30 months). Baseline `moving_average_3` repeats the latest three training months' mean. Candidate `trend_seasonal_regression` fits intercept, t/12, sin(2πt/12), cos(2πt/12) using ridge penalty 0.1 on non-intercept coefficients, clipping negative predictions to zero. Annual seasonality and linear trend are assumptions.

Default chronological validation trains through months 21 and 24, predicting the following three months at each origin. Both methods receive the same six targets per product. Select lowest validation MAE; ties favor baseline. Validation ends June 2026.

The final three months (July–September 2026) are untouched during selection. Fit the chosen method through June, predict the final holdout once and report independent test MAE/RMSE/MAPE. Finally refit the selected model on all 30 months and forecast October–December. The 18-month test fixture uses one validation origin at month 12 and final three-month holdout. Less than 18 months is rejected.

`forecast_validation` stores product, train end, target date, horizon, model, prediction and actual per candidate/origin. `forecast_test` stores the chosen model on the final holdout. `forecast_model_metrics` stores product/candidate validation scores and selected flag. `forecast_demand` stores future dates, horizons, predictions, null actual, selected model and its validation metrics. Future actuals are never invented. Actual results are in BUILD_VERIFICATION.md and `run_summary.json`.

MAPE excludes zero actuals and is sensitive to small intermittent quantities; high MAPE remains visible. Validation selection can underperform a baseline on a new window and does not guarantee improvement. No confidence intervals or claims of operational forecast accuracy are supplied.

Facility allocation uses each facility's share of a product's last three months' ordered demand; equal 20% shares apply if recent total is zero. This is an assumption. Allocations reconcile to each product forecast.

Projection is opening + expected receipts − allocated demand. First opening is latest on-hand; subsequent openings carry the previous ending, including deficits. Expected receipts are only known **open POs** in finished-unit equivalents, grouped by expected month. Overdue open POs are assumed received at next-month start. Received partial POs are closed and have no projected residual receipt. No speculative future production plan is added: planners must cover the resulting needs.

Receipts are available at month start and demand is consumed uniformly for stockout-date estimates. Historical inventory is reconciled monthly, not daily. Persist stockout flag/date, excess flag, days, replenishment and recommendations. Formulas are in KPI_DEFINITIONS.md and policies in settings. Negative projections are unmet requirements, never negative physical stock.
