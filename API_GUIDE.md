# FastAPI Guide

Start from the checkout: `python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000`. Interactive contract: [Swagger](http://127.0.0.1:8000/docs); machine contract: `/openapi.json`. All data is fictional/synthetic. Generate the warehouse before starting.

| Method / path | Result | Filters |
|---|---|---|
| GET `/health` | Database readiness and synthetic as-of | None |
| GET `/api/executive/summary` | Full-history KPIs plus live active exceptions | None; intentionally global snapshot |
| GET `/api/demand/trends` | Dense monthly product/facility demand | product_id, facility_id, month (YYYY-MM-01) |
| GET `/api/demand/forecast` | Product-level future demand and validation scores | product_id, horizon (1–3) |
| GET `/api/inventory/health` | Latest product/facility stock and historical statistics | product_id, facility_id |
| GET `/api/inventory/risks` | Projected shortage/surplus rows | product_id, facility_id, horizon, risk_type (stockout/excess/all) |
| GET `/api/suppliers/scorecard` | Full-history supplier metrics | supplier_id |
| GET `/api/logistics/performance` | Carrier/facility/route metrics | carrier_id, facility_id, route |
| GET `/api/facilities/performance` | Full-history facility metrics/latest stock and live open exceptions | facility_id |
| GET `/api/exceptions` | Severity-ordered operational exceptions | type, severity, status, facility_id, product_id, supplier_id |
| GET `/api/exceptions/{exception_id}` | One exception or 404 | Path ID |
| PATCH `/api/exceptions/{exception_id}` | Persisted workflow status | JSON status |
| POST `/api/assistant/query` | Structured evidence and explanation | JSON question, optional use_llm |

All list endpoints accept `limit` (default 100, maximum 1000) and `offset` (default 0). Response: `{data: [...], total: matching_count, limit, offset, synthetic_only: true}`. Empty matches return an empty list and zero count. IDs must be positive. Invalid dates, limits, enums and statuses return 422 with Pydantic details. Missing exceptions return 404; missing/failed warehouses return 503 with a meaningful recovery message. Queries parameterize all user values; table/column identifiers are fixed by implementation.

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/demand/trends?facility_id=5&limit=5'
$taskException = (Invoke-RestMethod 'http://127.0.0.1:8000/api/exceptions?severity=Critical&limit=1').data[0]
Invoke-RestMethod -Method Patch -Uri ('http://127.0.0.1:8000/api/exceptions/' + $taskException.exception_id) -ContentType 'application/json' -Body '{"status":"Investigating"}'
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/assistant/query' -ContentType 'application/json' -Body '{"question":"Why is OTIF low?"}'
```

PATCH is immediately committed and survives a rerun when the stable exception still triggers. It does not modify raw business records. Export CSVs are snapshots; rerun to refresh their statuses. Executive API recalculates active exception counts live. Ratios with undefined denominators are JSON null.

`python -m scripts.smoke_api` sends actual HTTP requests to the separately running server and saves the receipt. It changes one status, checks readback, then restores the original. Unit/integration endpoint tests also run against an isolated test warehouse.

Local demonstration only: bind to loopback. Authentication, authorization, rate limiting, workflow audit and CORS policy for a separate client would be needed before deployment. External LLM use is opt-in per request; the default calls no provider.
