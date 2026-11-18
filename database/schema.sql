PRAGMA foreign_keys = ON;

CREATE TABLE dim_customer (
  "customer_id" INTEGER NOT NULL,
  "customer_name" TEXT NOT NULL,
  "region" TEXT NOT NULL,
  "customer_segment" TEXT NOT NULL,
  PRIMARY KEY ("customer_id")
);

CREATE INDEX ix_dim_customer_customer_id ON dim_customer("customer_id");

CREATE TABLE dim_product (
  "product_id" INTEGER NOT NULL,
  "product_name" TEXT NOT NULL,
  "category" TEXT NOT NULL,
  "unit" TEXT NOT NULL,
  "standard_cost" REAL NOT NULL,
  "lead_time_days" INTEGER NOT NULL,
  "seasonal" INTEGER NOT NULL,
  PRIMARY KEY ("product_id")
);

CREATE INDEX ix_dim_product_product_id ON dim_product("product_id");

CREATE TABLE dim_supplier (
  "supplier_id" INTEGER NOT NULL,
  "supplier_name" TEXT NOT NULL,
  "region" TEXT NOT NULL,
  "default_lead_time_days" INTEGER NOT NULL,
  "supplier_tier" TEXT NOT NULL,
  PRIMARY KEY ("supplier_id")
);

CREATE INDEX ix_dim_supplier_supplier_id ON dim_supplier("supplier_id");

CREATE TABLE dim_facility (
  "facility_id" INTEGER NOT NULL,
  "facility_name" TEXT NOT NULL,
  "city" TEXT NOT NULL,
  "capacity" INTEGER NOT NULL,
  PRIMARY KEY ("facility_id")
);

CREATE INDEX ix_dim_facility_facility_id ON dim_facility("facility_id");

CREATE TABLE dim_carrier (
  "carrier_id" INTEGER NOT NULL,
  "carrier_name" TEXT NOT NULL,
  "mode" TEXT NOT NULL,
  PRIMARY KEY ("carrier_id")
);

CREATE INDEX ix_dim_carrier_carrier_id ON dim_carrier("carrier_id");

CREATE TABLE bridge_supplier_product (
  "supplier_product_id" INTEGER NOT NULL,
  "supplier_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  FOREIGN KEY ("supplier_id") REFERENCES dim_supplier ("supplier_id"),
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  PRIMARY KEY ("supplier_product_id"),
  UNIQUE(supplier_id,product_id)
);

CREATE INDEX ix_bridge_supplier_product_supplier_id ON bridge_supplier_product("supplier_id");

CREATE INDEX ix_bridge_supplier_product_product_id ON bridge_supplier_product("product_id");

CREATE TABLE fact_sales_order (
  "line_id" INTEGER NOT NULL,
  "order_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  "ordered_quantity" INTEGER NOT NULL,
  "fulfilled_quantity" INTEGER NOT NULL,
  "order_date" TEXT NOT NULL,
  "customer_id" INTEGER NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "required_date" TEXT NOT NULL,
  "status" TEXT NOT NULL,
  "backlog_quantity" INTEGER NOT NULL,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  CHECK ("ordered_quantity" >= 0),
  CHECK ("fulfilled_quantity" >= 0),
  FOREIGN KEY ("order_date") REFERENCES dim_date (date),
  FOREIGN KEY ("customer_id") REFERENCES dim_customer ("customer_id"),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("required_date") REFERENCES dim_date (date),
  CHECK ("backlog_quantity" >= 0),
  PRIMARY KEY ("line_id"),
  CHECK(ordered_quantity > 0),
  CHECK(fulfilled_quantity <= ordered_quantity),
  CHECK(backlog_quantity = ordered_quantity - fulfilled_quantity),
  CHECK(required_date >= order_date),
  CHECK(status IN ('Open','Fulfilled'))
);

CREATE INDEX ix_fact_sales_order_product_id ON fact_sales_order("product_id");

CREATE INDEX ix_fact_sales_order_order_date ON fact_sales_order("order_date");

CREATE INDEX ix_fact_sales_order_customer_id ON fact_sales_order("customer_id");

CREATE INDEX ix_fact_sales_order_facility_id ON fact_sales_order("facility_id");

CREATE INDEX ix_fact_sales_order_required_date ON fact_sales_order("required_date");

CREATE TABLE fact_production (
  "production_id" INTEGER NOT NULL,
  "production_date" TEXT NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  "planned_quantity" INTEGER NOT NULL,
  "produced_quantity" INTEGER NOT NULL,
  "status" TEXT NOT NULL,
  FOREIGN KEY ("production_date") REFERENCES dim_date (date),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  CHECK ("planned_quantity" >= 0),
  CHECK ("produced_quantity" >= 0),
  PRIMARY KEY ("production_id")
);

CREATE INDEX ix_fact_production_production_date ON fact_production("production_date");

CREATE INDEX ix_fact_production_facility_id ON fact_production("facility_id");

CREATE INDEX ix_fact_production_product_id ON fact_production("product_id");

CREATE TABLE fact_inventory (
  "inventory_id" INTEGER NOT NULL,
  "snapshot_date" TEXT NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  "opening_quantity" INTEGER NOT NULL,
  "production_quantity" INTEGER NOT NULL,
  "receipt_quantity" INTEGER NOT NULL,
  "consumed_quantity" INTEGER NOT NULL,
  "on_hand_quantity" INTEGER NOT NULL,
  FOREIGN KEY ("snapshot_date") REFERENCES dim_date (date),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  CHECK ("opening_quantity" >= 0),
  CHECK ("production_quantity" >= 0),
  CHECK ("receipt_quantity" >= 0),
  CHECK ("consumed_quantity" >= 0),
  CHECK ("on_hand_quantity" >= 0),
  PRIMARY KEY ("inventory_id"),
  UNIQUE(snapshot_date, product_id, facility_id),
  CHECK(on_hand_quantity = opening_quantity + production_quantity + receipt_quantity - consumed_quantity)
);

CREATE INDEX ix_fact_inventory_snapshot_date ON fact_inventory("snapshot_date");

CREATE INDEX ix_fact_inventory_facility_id ON fact_inventory("facility_id");

CREATE INDEX ix_fact_inventory_product_id ON fact_inventory("product_id");

CREATE TABLE fact_purchase_order (
  "po_id" INTEGER NOT NULL,
  "supplier_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "order_date" TEXT NOT NULL,
  "expected_date" TEXT NOT NULL,
  "ordered_quantity" INTEGER NOT NULL,
  "status" TEXT NOT NULL,
  FOREIGN KEY ("supplier_id") REFERENCES dim_supplier ("supplier_id"),
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("order_date") REFERENCES dim_date (date),
  FOREIGN KEY ("expected_date") REFERENCES dim_date (date),
  CHECK ("ordered_quantity" >= 0),
  PRIMARY KEY ("po_id"),
  CHECK(expected_date >= order_date),
  CHECK(status IN ('Open','Received'))
);

CREATE INDEX ix_fact_purchase_order_supplier_id ON fact_purchase_order("supplier_id");

CREATE INDEX ix_fact_purchase_order_product_id ON fact_purchase_order("product_id");

CREATE INDEX ix_fact_purchase_order_facility_id ON fact_purchase_order("facility_id");

CREATE INDEX ix_fact_purchase_order_order_date ON fact_purchase_order("order_date");

CREATE INDEX ix_fact_purchase_order_expected_date ON fact_purchase_order("expected_date");

CREATE TABLE fact_supplier_delivery (
  "delivery_id" INTEGER NOT NULL,
  "po_id" INTEGER NOT NULL,
  "supplier_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "delivery_date" TEXT NOT NULL,
  "delivered_quantity" INTEGER NOT NULL,
  "order_date" TEXT NOT NULL,
  "expected_date" TEXT NOT NULL,
  "ordered_quantity" INTEGER NOT NULL,
  "lead_time_days" INTEGER NOT NULL,
  "delay_days" INTEGER NOT NULL,
  "on_time" INTEGER NOT NULL,
  "in_full" INTEGER NOT NULL,
  "otif" INTEGER NOT NULL,
  FOREIGN KEY ("supplier_id") REFERENCES dim_supplier ("supplier_id"),
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("delivery_date") REFERENCES dim_date (date),
  CHECK ("delivered_quantity" >= 0),
  FOREIGN KEY ("order_date") REFERENCES dim_date (date),
  FOREIGN KEY ("expected_date") REFERENCES dim_date (date),
  CHECK ("ordered_quantity" >= 0),
  CHECK ("lead_time_days" >= 0),
  CHECK ("delay_days" >= 0),
  CHECK ("on_time" IN (0,1)),
  CHECK ("in_full" IN (0,1)),
  CHECK ("otif" IN (0,1)),
  PRIMARY KEY ("delivery_id"),
  FOREIGN KEY(po_id) REFERENCES fact_purchase_order(po_id),
  UNIQUE(po_id),
  CHECK(delivery_date >= order_date),
  CHECK(otif = on_time * in_full)
);

CREATE INDEX ix_fact_supplier_delivery_supplier_id ON fact_supplier_delivery("supplier_id");

CREATE INDEX ix_fact_supplier_delivery_product_id ON fact_supplier_delivery("product_id");

CREATE INDEX ix_fact_supplier_delivery_facility_id ON fact_supplier_delivery("facility_id");

CREATE INDEX ix_fact_supplier_delivery_delivery_date ON fact_supplier_delivery("delivery_date");

CREATE INDEX ix_fact_supplier_delivery_order_date ON fact_supplier_delivery("order_date");

CREATE INDEX ix_fact_supplier_delivery_expected_date ON fact_supplier_delivery("expected_date");

CREATE TABLE fact_shipment (
  "shipment_id" INTEGER NOT NULL,
  "line_id" INTEGER NOT NULL,
  "order_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "carrier_id" INTEGER NOT NULL,
  "ship_date" TEXT NOT NULL,
  "promised_date" TEXT NOT NULL,
  "actual_delivery_date" TEXT NOT NULL,
  "shipped_quantity" INTEGER NOT NULL,
  "delivered_quantity" INTEGER NOT NULL,
  "route" TEXT NOT NULL,
  "ordered_quantity" INTEGER NOT NULL,
  "delay_days" INTEGER NOT NULL,
  "on_time" INTEGER NOT NULL,
  "in_full" INTEGER NOT NULL,
  "otif" INTEGER NOT NULL,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("carrier_id") REFERENCES dim_carrier ("carrier_id"),
  FOREIGN KEY ("ship_date") REFERENCES dim_date (date),
  FOREIGN KEY ("promised_date") REFERENCES dim_date (date),
  FOREIGN KEY ("actual_delivery_date") REFERENCES dim_date (date),
  CHECK ("shipped_quantity" >= 0),
  CHECK ("delivered_quantity" >= 0),
  CHECK ("ordered_quantity" >= 0),
  CHECK ("delay_days" >= 0),
  CHECK ("on_time" IN (0,1)),
  CHECK ("in_full" IN (0,1)),
  CHECK ("otif" IN (0,1)),
  PRIMARY KEY ("shipment_id"),
  FOREIGN KEY(line_id) REFERENCES fact_sales_order(line_id),
  UNIQUE(line_id),
  CHECK(actual_delivery_date >= ship_date),
  CHECK(delivered_quantity <= shipped_quantity),
  CHECK(otif = on_time * in_full)
);

CREATE INDEX ix_fact_shipment_product_id ON fact_shipment("product_id");

CREATE INDEX ix_fact_shipment_facility_id ON fact_shipment("facility_id");

CREATE INDEX ix_fact_shipment_carrier_id ON fact_shipment("carrier_id");

CREATE INDEX ix_fact_shipment_ship_date ON fact_shipment("ship_date");

CREATE INDEX ix_fact_shipment_promised_date ON fact_shipment("promised_date");

CREATE INDEX ix_fact_shipment_actual_delivery_date ON fact_shipment("actual_delivery_date");

CREATE TABLE dim_date (
  "date_id" INTEGER NOT NULL,
  "date" TEXT NOT NULL,
  "year" INTEGER NOT NULL,
  "month" INTEGER NOT NULL,
  "quarter" INTEGER NOT NULL,
  "month_start" TEXT NOT NULL,
  PRIMARY KEY ("date_id"),
  UNIQUE (date)
);

CREATE TABLE agg_demand (
  "month" TEXT NOT NULL,
  "product_id" INTEGER NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "demand_quantity" INTEGER,
  "fulfilled_quantity" INTEGER,
  "backlog_quantity" INTEGER,
  "previous_demand" REAL,
  "demand_growth" REAL,
  "demand_volatility" REAL,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  PRIMARY KEY ("month", "product_id", "facility_id")
);

CREATE INDEX ix_agg_demand_product_id ON agg_demand("product_id");

CREATE INDEX ix_agg_demand_facility_id ON agg_demand("facility_id");

CREATE TABLE agg_inventory (
  "inventory_id" INTEGER,
  "snapshot_date" TEXT,
  "facility_id" INTEGER NOT NULL,
  "product_id" INTEGER NOT NULL,
  "opening_quantity" INTEGER,
  "production_quantity" INTEGER,
  "receipt_quantity" INTEGER,
  "consumed_quantity" INTEGER,
  "on_hand_quantity" INTEGER,
  "average_inventory" REAL,
  "stockout_count" INTEGER,
  "demand_quantity" REAL,
  "fulfilled_quantity" REAL,
  "standard_cost" REAL,
  "average_daily_demand" REAL,
  "days_of_inventory" REAL,
  "current_days_of_inventory" REAL,
  "inventory_value" REAL,
  "average_inventory_value" REAL,
  "synthetic_cogs_proxy" REAL,
  "inventory_turnover" REAL,
  "excess_inventory" INTEGER,
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  PRIMARY KEY ("product_id", "facility_id")
);

CREATE INDEX ix_agg_inventory_facility_id ON agg_inventory("facility_id");

CREATE INDEX ix_agg_inventory_product_id ON agg_inventory("product_id");

CREATE TABLE agg_supplier (
  "supplier_id" INTEGER NOT NULL,
  "supplier_name" TEXT,
  "region" TEXT,
  "default_lead_time_days" INTEGER,
  "supplier_tier" TEXT,
  "deliveries" INTEGER,
  "otif_count" INTEGER,
  "on_time_count" INTEGER,
  "average_lead_time" REAL,
  "lead_time_variance" REAL,
  "late_count" INTEGER,
  "delivered_quantity" INTEGER,
  "ordered_quantity" INTEGER,
  "supplier_otif" REAL,
  "late_delivery_rate" REAL,
  "fill_rate" REAL,
  FOREIGN KEY ("supplier_id") REFERENCES dim_supplier ("supplier_id"),
  PRIMARY KEY ("supplier_id")
);

CREATE INDEX ix_agg_supplier_supplier_id ON agg_supplier("supplier_id");

CREATE TABLE agg_logistics (
  "carrier_id" INTEGER NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "route" TEXT NOT NULL,
  "shipments" INTEGER,
  "otif_count" INTEGER,
  "late_count" INTEGER,
  "average_delivery_delay" REAL,
  "ordered_quantity" INTEGER,
  "delivered_quantity" INTEGER,
  "logistics_otif" REAL,
  "late_shipment_rate" REAL,
  "fill_rate" REAL,
  FOREIGN KEY ("carrier_id") REFERENCES dim_carrier ("carrier_id"),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  PRIMARY KEY ("carrier_id", "facility_id", "route")
);

CREATE INDEX ix_agg_logistics_carrier_id ON agg_logistics("carrier_id");

CREATE INDEX ix_agg_logistics_facility_id ON agg_logistics("facility_id");

CREATE TABLE agg_facility (
  "facility_id" INTEGER NOT NULL,
  "facility_name" TEXT,
  "production_quantity" INTEGER,
  "planned_quantity" INTEGER,
  "production_attainment" REAL,
  "demand_quantity" INTEGER,
  "inventory_quantity" INTEGER,
  "latest_production" INTEGER,
  "latest_planned" INTEGER,
  "latest_production_attainment" REAL,
  "order_count" INTEGER,
  "fulfilled_orders" INTEGER,
  "open_orders" INTEGER,
  "overdue_orders" INTEGER,
  "fulfillment_rate" REAL,
  "backlog_quantity" INTEGER,
  "fill_rate" REAL,
  "exceptions" INTEGER,
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  PRIMARY KEY ("facility_id")
);

CREATE INDEX ix_agg_facility_facility_id ON agg_facility("facility_id");

CREATE TABLE executive_kpis (
  "as_of" TEXT NOT NULL,
  "history_days" INTEGER,
  "total_demand" INTEGER,
  "inventory_quantity" INTEGER,
  "inventory_value" REAL,
  "average_inventory_quantity" REAL,
  "synthetic_cogs_proxy" REAL,
  "inventory_turnover" REAL,
  "days_of_inventory" REAL,
  "supplier_otif" REAL,
  "logistics_otif" REAL,
  "late_shipment_rate" REAL,
  "average_delivery_delay" REAL,
  "shipment_count" INTEGER,
  "stockout_count" INTEGER,
  "excess_inventory_pairs" INTEGER,
  "order_count" INTEGER,
  "fulfilled_orders" INTEGER,
  "open_orders" INTEGER,
  "overdue_orders" INTEGER,
  "fulfillment_rate" REAL,
  "backlog_quantity" INTEGER,
  "fill_rate" REAL,
  "stockout_risk_pairs" INTEGER,
  "open_exceptions" INTEGER,
  PRIMARY KEY ("as_of")
);

CREATE TABLE forecast_demand (
  "product_id" INTEGER NOT NULL,
  "train_end" TEXT,
  "forecast_date" TEXT,
  "horizon" INTEGER NOT NULL,
  "prediction" REAL,
  "actual" TEXT,
  "model_name" TEXT,
  "mae" REAL,
  "rmse" REAL,
  "mape" REAL,
  "mape_eligible_count" INTEGER,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  PRIMARY KEY ("product_id", "horizon")
);

CREATE INDEX ix_forecast_demand_product_id ON forecast_demand("product_id");

CREATE TABLE forecast_validation (
  "product_id" INTEGER NOT NULL,
  "train_end" TEXT NOT NULL,
  "forecast_date" TEXT,
  "horizon" INTEGER NOT NULL,
  "prediction" REAL,
  "actual" REAL,
  "model_name" TEXT NOT NULL,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  PRIMARY KEY ("product_id", "model_name", "train_end", "horizon")
);

CREATE INDEX ix_forecast_validation_product_id ON forecast_validation("product_id");

CREATE TABLE forecast_model_metrics (
  "product_id" INTEGER NOT NULL,
  "model_name" TEXT NOT NULL,
  "mae" REAL,
  "rmse" REAL,
  "mape" REAL,
  "mape_eligible_count" INTEGER,
  "selected" INTEGER,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  PRIMARY KEY ("product_id", "model_name")
);

CREATE INDEX ix_forecast_model_metrics_product_id ON forecast_model_metrics("product_id");

CREATE TABLE forecast_test (
  "product_id" INTEGER NOT NULL,
  "train_end" TEXT,
  "forecast_date" TEXT,
  "horizon" INTEGER NOT NULL,
  "prediction" REAL,
  "actual" REAL,
  "model_name" TEXT,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  PRIMARY KEY ("product_id", "horizon")
);

CREATE INDEX ix_forecast_test_product_id ON forecast_test("product_id");

CREATE TABLE projected_inventory (
  "product_id" INTEGER NOT NULL,
  "facility_id" INTEGER NOT NULL,
  "forecast_date" TEXT,
  "horizon" INTEGER NOT NULL,
  "opening_inventory" REAL,
  "expected_receipts" REAL,
  "forecast_demand" REAL,
  "projected_ending_inventory" REAL,
  "stockout_flag" INTEGER,
  "stockout_date" TEXT,
  "days_of_inventory" REAL,
  "excess_inventory_flag" INTEGER,
  "replenishment_quantity" INTEGER,
  "recommendation" TEXT,
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  CHECK ("stockout_flag" IN (0,1)),
  CHECK ("excess_inventory_flag" IN (0,1)),
  PRIMARY KEY ("product_id", "facility_id", "horizon")
);

CREATE INDEX ix_projected_inventory_product_id ON projected_inventory("product_id");

CREATE INDEX ix_projected_inventory_facility_id ON projected_inventory("facility_id");

CREATE TABLE supply_chain_exception (
  "exception_id" TEXT NOT NULL,
  "type" TEXT,
  "severity" TEXT,
  "facility_id" INTEGER,
  "product_id" INTEGER,
  "supplier_id" INTEGER,
  "reference" TEXT,
  "detected_date" TEXT,
  "metric" TEXT,
  "threshold" REAL,
  "actual_value" REAL,
  "expected_value" REAL,
  "status" TEXT,
  "recommended_action" TEXT,
  FOREIGN KEY ("facility_id") REFERENCES dim_facility ("facility_id"),
  FOREIGN KEY ("product_id") REFERENCES dim_product ("product_id"),
  FOREIGN KEY ("supplier_id") REFERENCES dim_supplier ("supplier_id"),
  PRIMARY KEY ("exception_id"),
  CHECK(status IN ('Open','Investigating','Resolved','Accepted')),
  CHECK(severity IN ('Critical','High','Medium','Low'))
);

CREATE INDEX ix_supply_chain_exception_facility_id ON supply_chain_exception("facility_id");

CREATE INDEX ix_supply_chain_exception_product_id ON supply_chain_exception("product_id");

CREATE INDEX ix_supply_chain_exception_supplier_id ON supply_chain_exception("supplier_id");

CREATE INDEX ix_exception_status_severity ON supply_chain_exception(status,severity);

CREATE INDEX ix_sales_order_id ON fact_sales_order(order_id);
