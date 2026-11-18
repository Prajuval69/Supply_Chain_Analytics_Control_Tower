# MASTER PROMPT — Supply Chain Analytics & Control Tower

Build a complete portfolio-grade **Supply Chain Analytics & Control Tower** for a fictional packaging manufacturer named **PackRight Manufacturing**.

The system must demonstrate Python, SQL, ETL/data pipelines, data cleaning, supply-chain analytics, inventory analytics, supplier analytics, logistics analytics, demand forecasting, inventory projection, exception detection, Power BI-ready reporting, FastAPI, testing, documentation, and an optional GenAI analytics assistant.

## Critical constraints

- Use synthetic data only.
- Never claim to use confidential Greif data.
- Run locally without mandatory cloud infrastructure.
- The core project must work without an LLM API key.
- Do not create a fake Power BI `.pbix`; generate import-ready datasets and a Power BI guide if Power BI Desktop is unavailable.
- Do not stop at scaffolding: implement, execute, test, debug, verify, and document the entire system.
- Keep the design explainable for a B.Tech Data Science fresher.

## Business scenario

PackRight has:
- customers
- products
- suppliers
- manufacturing facilities
- sales orders
- production
- inventory
- purchase orders
- supplier deliveries
- shipments
- carriers

Suggested facilities: Chennai, Hyderabad, Pune, Mumbai, Bengaluru.

Suggested product categories:
- Fiber Packaging
- Metal Containers
- Polymer Packaging
- Industrial Drums
- Intermediate Bulk Containers

## Source systems

Simulate:
1. ERP — customers, products, sales orders, order lines, purchase orders
2. MES — production orders and production quantities
3. WMS — inventory snapshots
4. Supplier Management — suppliers, supplier products, lead times, purchase orders, deliveries
5. Logistics — shipments, promised dates, actual delivery dates, carriers, routes

Store raw data under `data/raw/<source>/`.

## Synthetic data

Use a fixed random seed and generate at least 18 months of history.

Suggested minimum:
- 500 customers
- 200 products
- 100 suppliers
- 5 facilities
- 15 carriers
- 10,000 sales orders
- 20,000 order lines
- 10,000 production records
- 20,000 inventory snapshots
- 5,000 purchase orders
- 5,000 supplier deliveries
- 10,000 shipments

Do not generate purely random data. Build realistic relationships:
- demand influences production
- production and receipts influence inventory
- supplier lead time influences delivery
- carrier behavior influences shipment delay
- some products are seasonal
- some suppliers systematically perform worse
- some facilities have recurring stockout risk

Inject controlled defects such as missing IDs, duplicate orders, negative inventory, invalid dates, invalid references, and inconsistent categories.

## ETL

Implement:

`raw → staging → cleaned → curated → analytics`

Stages:
1. ingestion
2. schema validation
3. profiling
4. cleaning
5. standardization
6. transformation
7. warehouse loading
8. KPI calculation
9. forecasting
10. inventory projection
11. exception generation
12. reporting export

Make reruns reproducible and preferably idempotent.

## Database

Use SQLite by default with a star-schema-style model.

Dimensions:
- dim_date
- dim_customer
- dim_product
- dim_supplier
- dim_facility
- dim_carrier

Facts:
- fact_sales_order
- fact_production
- fact_inventory
- fact_purchase_order
- fact_supplier_delivery
- fact_shipment

Analytics:
- agg_demand
- agg_inventory
- agg_supplier
- agg_logistics
- agg_facility
- forecast_demand
- projected_inventory
- supply_chain_exception

Use sensible keys, constraints, and indexes.

## KPIs

Implement and document:

Demand:
- total demand
- monthly demand
- demand growth
- demand volatility
- demand by product/facility

Inventory:
- quantity
- average inventory
- inventory turnover
- days of inventory
- stockout count
- excess inventory
- projected stockout date

Supplier:
- supplier OTIF
- average lead time
- lead-time variance
- late delivery rate
- fill rate

Orders:
- order count
- fulfilled orders
- open orders
- overdue orders
- fulfillment rate
- backlog quantity

Logistics:
- shipments
- OTIF
- average delivery delay
- late shipment rate
- carrier performance

Facility:
- production
- demand
- inventory
- fulfillment
- backlog
- exceptions

Document every formula. OTIF must require both on-time delivery and in-full quantity. Clearly label any synthetic COGS proxy used for inventory turnover.

## Forecasting

Forecast product demand for 1–3 months.

Implement a simple baseline first, then a lightweight method such as exponential smoothing or regression with time/lag features.

Evaluate using:
- MAE
- RMSE
- MAPE when meaningful

Select the model based on validation performance.

Persist forecast date, product, horizon, prediction, actual where available, model name, and metrics.

## Inventory projection

Use:

`projected_inventory = current_inventory + expected_receipts - forecast_demand`

Generate:
- projected ending inventory
- stockout flag/date
- excess inventory flag
- replenishment recommendation

Use configurable thresholds.

## Exceptions

Generate:
- STOCKOUT_RISK
- EXCESS_INVENTORY
- SUPPLIER_DELAY
- SHIPMENT_DELAY
- ORDER_BACKLOG
- LOW_SUPPLIER_OTIF
- HIGH_DEMAND_VOLATILITY
- PRODUCTION_SHORTFALL

Fields:
exception_id, type, severity, facility, product, supplier, reference, detected_date, metric, threshold, actual_value, expected_value, status, recommended_action.

Statuses: Open, Investigating, Resolved, Accepted.

Create deterministic recommendations for each type.

## Power BI

Generate under `outputs/powerbi/`:
- executive_kpis.csv
- demand_trends.csv
- inventory_health.csv
- supplier_scorecard.csv
- logistics_performance.csv
- facility_performance.csv
- forecast_demand.csv
- projected_inventory.csv
- supply_chain_exceptions.csv

Create a six-page guide:
1. Executive Control Tower
2. Demand & Forecast
3. Inventory Health
4. Supplier Scorecard
5. Logistics
6. Exceptions

Include recommended measures, relationships, visuals, filters, and business questions.

## FastAPI

Implement:
- GET `/health`
- GET `/api/executive/summary`
- GET `/api/demand/trends`
- GET `/api/demand/forecast`
- GET `/api/inventory/health`
- GET `/api/inventory/risks`
- GET `/api/suppliers/scorecard`
- GET `/api/logistics/performance`
- GET `/api/facilities/performance`
- GET `/api/exceptions`
- GET `/api/exceptions/{exception_id}`
- PATCH `/api/exceptions/{exception_id}`

Use Pydantic and meaningful errors.

## Optional GenAI assistant

Build a **Supply Chain Analytics Assistant** that can answer questions such as:
- Which products have the highest stockout risk?
- Which suppliers are underperforming?
- Why is OTIF low?
- Which facility has the largest backlog?
- What demand is expected next month?
- Which products have excess inventory?
- What are the most critical exceptions?

Use structured project data for retrieval. LLM use must be optional. Implement a deterministic fallback so the feature works without credentials.

## Testing

Create at least 30 meaningful tests covering:
- generation
- relationships
- cleaning
- transformations
- KPI formulas
- OTIF
- fill rate
- inventory turnover
- demand aggregation
- forecasting
- forecast metrics
- projected inventory
- stockout logic
- exception generation
- database loading
- API endpoints
- AI fallback
- pipeline idempotency

Do not create fake tests.

## Project structure

Use a clean structure such as:

```text
project/
├── README.md
├── MASTER_PROMPT.md
├── PROJECT_SPEC.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
├── data/{raw,staging,processed,reference}/
├── database/schema.sql
├── src/{api,data,pipeline,analytics,forecasting,inventory,suppliers,logistics,exceptions,reporting,ai,db,utils}/
├── tests/
├── outputs/{powerbi,reports,forecasts}/
├── docs/
└── logs/
```

## Documentation

Create:
- README.md
- ARCHITECTURE.md
- DATA_DICTIONARY.md
- KPI_DEFINITIONS.md
- FORECASTING.md
- POWER_BI_GUIDE.md
- API_GUIDE.md
- EXCEPTIONS.md
- AI_ASSISTANT.md
- TESTING.md
- PROJECT_WALKTHROUGH.md
- BUILD_VERIFICATION.md

## Mandatory execution

After implementation:
1. install dependencies
2. generate data
3. run complete ETL
4. populate database
5. calculate KPIs
6. evaluate forecasting
7. project inventory
8. generate exceptions
9. export Power BI datasets
10. run all tests
11. smoke-test FastAPI
12. inspect outputs
13. fix failures
14. check for secrets/hardcoded paths
15. update docs with actual results

Do not claim execution unless it actually happened.

## Acceptance criteria

The project is complete only when:
- multi-source synthetic data exists
- 18+ months are represented
- realistic relationships exist
- controlled defects exist
- ETL works
- SQL analytical model works
- demand/inventory/supplier/logistics/facility analytics work
- forecasting is evaluated
- projected inventory works
- stockout/excess risks work
- exceptions work
- Power BI-ready outputs exist
- FastAPI works
- AI fallback works
- 30+ meaningful tests pass
- full pipeline has actually run
- documentation is complete
- no secrets are committed

At the end, report actual record counts, KPI results, selected forecast model and metrics, exception counts, tests passed, API status, output locations, limitations, and reproduction commands.
