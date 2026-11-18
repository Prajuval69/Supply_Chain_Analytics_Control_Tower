# Supply Chain Analytics & Control Tower

PackRight Manufacturing is fictional. **Every record is synthetic. This project does not use confidential Greif data or represent Greif's internal systems.**

This locally runnable Python/SQLite system unifies ERP orders, MES production, WMS inventory, supplier procurement and logistics. It cleans sources, builds a constrained warehouse, calculates KPIs, evaluates forecasts, projects inventory, detects exceptions and exports a six-page Power BI model. FastAPI exposes the results; the analytics assistant works without credentials.

## Public project overview

[Live project overview](https://prajuval69.github.io/Supply_Chain_Analytics_Control_Tower/) · [Public repository](https://github.com/Prajuval69/Supply_Chain_Analytics_Control_Tower)

The website is a static overview of the recorded synthetic results. Run the pipeline and FastAPI locally for interactive analytics and workflow updates.

## Run locally

Python 3.11+; verified on Windows/Python 3.12.4. Run from the project directory:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe -m pip install --no-deps -e .
.venv/Scripts/python.exe -m src.pipeline.run
.venv/Scripts/python.exe -m pytest --junitxml=outputs/reports/pytest.xml
.venv/Scripts/python.exe -m scripts.audit_outputs
.venv/Scripts/python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

In a second terminal run `.venv/Scripts/python.exe -m scripts.smoke_api`. Open [Swagger](http://127.0.0.1:8000/docs). On macOS/Linux substitute `.venv/bin/python`. The environment needs no activation.

Use `python -m src.pipeline.run --skip-generate` to process existing raw data. `--root PATH` chooses another artifact root; set `PACKRIGHT_ROOT` to the same directory for the API and verification scripts. Configuration lives in `config/settings.json`. Run the pipeline serially; stop database clients before replacement on Windows if they hold file locks. The default CLI regenerates the data and all outputs while preserving exception statuses.

## Implemented capabilities

- Fixed-seed, demand-driven 30-month simulation, including seasonality, weaker suppliers, slow carriers, production shortfalls and surplus SKUs.
- Raw → staging → cleaned → curated → analytics, with contracts, quarantine files and before/after profiles.
- Six dimensions, six facts, supplier-product bridge, domain aggregates, forecasts, projections and exceptions; SQL keys, checks, foreign keys and indexes.
- Six analytics domains with explicit grains and weighted denominators.
- Moving-average baseline versus trend/seasonality regression, chronological validation, independent final holdout and per-product model selection.
- Three-month inventory scenario, crossing dates, excess flags, replenishment recommendations and eight exception types with persisted statuses.
- Required API endpoints, filters, pagination, validated status updates, structured assistant retrieval and optional provider explanations.
- Power BI CSVs, theme, Power Query loader, DAX measures and complete six-page specification.

## Evidence and output locations

[BUILD_VERIFICATION.md](BUILD_VERIFICATION.md) contains actual counts, KPIs, forecast metrics, tests, real HTTP smoke checks and output audits. [BUILD_CHECKLIST.md](BUILD_CHECKLIST.md) is verified from those receipts.

| Location | Contents |
|---|---|
| `data/raw/<source>/` | Simulated source files with controlled defects |
| `data/staging/` | Ingested source copies |
| `data/processed/` | Cleaned source tables |
| `data/curated/` | Star and analytics CSVs |
| `data/reference/` | Seed/dates and defect manifest |
| `database/control_tower.sqlite` | Validated warehouse |
| `database/schema.sql` | Actual executed DDL, recreated by pipeline |
| `outputs/powerbi/` | Nine required exports plus dimensions, facts and evaluations |
| `outputs/forecasts/` | Future/validation/test predictions, model scores and projections |
| `outputs/reports/` | Run summary, profiles, quarantines, integrity, audit, HTTP smoke and pytest XML |
| `logs/pipeline.log` | Actual stage log |

Generated data and local environments are Git-ignored; clone users regenerate them. Source, tests, specifications, SQL and documentation are the portfolio assets. No PBIX or screenshot is fabricated.

## Documentation

[Architecture](ARCHITECTURE.md), [dictionary](DATA_DICTIONARY.md), [formulas](KPI_DEFINITIONS.md), [forecasting](FORECASTING.md), [Power BI](POWER_BI_GUIDE.md), [API](API_GUIDE.md), [exceptions](EXCEPTIONS.md), [assistant](AI_ASSISTANT.md), [testing](TESTING.md), [walkthrough](PROJECT_WALKTHROUGH.md), [interview guide](INTERVIEW_GUIDE.md).

## Practical limits

This is a monthly planning demonstration without production authentication, real-time ingestion or deployment. Inventory reconciles at month end and does not claim intramonth physical feasibility. Procurement represents finished-unit equivalent receipts, not component bills of materials. Old unfilled orders remain backlog; later supply does not retroactively clear them. Sparse-SKU forecasts can have substantial error. Projection includes known open POs and no future production plan, so modeled shortages require planner review. Turnover uses a full-history synthetic cost proxy and is not annualized.

Power BI Desktop was not found in checked executable/install locations. Reporting assets are supplied; DAX, visuals and refresh require Desktop verification. No external LLM call was made; deterministic fallback and mocked provider failures are tested.
