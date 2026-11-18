# Interview Guide

## 30-second explanation

"I built a fictional supply-chain control tower integrating simulated ERP, production, warehouse, supplier, and logistics data. I built a Python and SQL pipeline to clean and transform the data, calculated operational KPIs, added demand forecasting and projected inventory, and generated exceptions for stockout, supplier, shipment, and backlog risks. The results are exposed through FastAPI and prepared for a Power BI control tower."

## Why?
"To demonstrate both data engineering and business analytics rather than only a dashboard."

## Why synthetic data?
"To avoid confidential data while still modeling realistic supply-chain relationships."

## OTIF
"A shipment is OTIF when it arrives by the promised date and the delivered quantity meets or exceeds the required quantity."

## Forecasting
"I established a simple baseline, compared it with a lightweight forecasting approach, and selected based on validation metrics."

## Stockout risk
"I project ending inventory using current inventory plus expected receipts minus forecast demand and flag products crossing the configured risk threshold."

## Improvements
Cloud warehouse, real-time ingestion, probabilistic forecasting, supplier collaboration, alerting, data contracts, CI/CD, and production monitoring.
