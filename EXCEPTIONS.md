# Supply Chain Exception Framework

The deterministic engine supports synthetic-data triage, without external alerts or autonomous operational actions.

| Type | Trigger | Severity | Recommendation |
|---|---|---|---|
| STOCKOUT_RISK | First horizon ending ≤ stockout threshold | Critical for horizon 1, High otherwise | Expedite receipts, schedule production, rebalance |
| EXCESS_INVENTORY | First horizon days > excess limit; or positive stock with zero forecast | Low | Reduce replenishment/production, transfer surplus |
| SUPPLIER_DELAY | Latest-month delivery delay > limit; or open PO overdue > limit | High for delay > 7 days or overdue PO, otherwise Medium | Confirm recovery and alternate sourcing |
| SHIPMENT_DELAY | Latest-month delivery delay > limit | High when > 7 days, otherwise Medium | Contact carrier, review route/customer recovery |
| ORDER_BACKLOG | Overdue line backlog > quantity limit | Critical when > 30 days overdue, otherwise High | Prioritize aged orders, reconcile supply/capacity |
| LOW_SUPPLIER_OTIF | Full-history supplier OTIF < rate limit | High | Review failures and alternate allocations |
| HIGH_DEMAND_VOLATILITY | Product-level sample monthly CV > ratio limit | Medium | Review seasonal drivers, stock and errors |
| PRODUCTION_SHORTFALL | Latest-month produced/planned < attainment limit, positive plan only | High below 0.8, otherwise Medium | Investigate downtime, materials and schedule |

Defaults: 0 units, 90 days, 3 delay days, 30 backlog units, 0.75 OTIF, 0.45 CV, 0.90 attainment. All are configurable. Historical completed delays are limited to latest month; backlog is cumulative by simulation design. First stockout/excess triggers once per product/facility across the horizon. Excess metric compares ending quantity with the excess-days equivalent target so zero demand has a valid numeric comparison.

Each row contains exception_id, type, severity, nullable facility/product/supplier IDs, reference, detected_date, metric, threshold, actual_value, expected_value, status and recommended_action. Detected date is synthetic as-of. Stable ID is `EX-` plus 16 hex characters of SHA-256(type + reference). Actions are defined in `src/exceptions/engine.py` and returned unchanged.

Statuses: Open, Investigating, Resolved, Accepted. PATCH allows any of these demonstration states and rejects invalid states with 422. SQLite persists changes, executive API counts active statuses live, and pipeline reruns preserve statuses for still-triggering IDs. Non-triggering exceptions are not archived. This snapshot model has no user/audit history. CSVs reflect export time and refresh on rerun.
