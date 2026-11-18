"""One contract per source table: primary key, date/numeric fields, foreign keys."""
CONTRACTS = {
    "customers": ("customer_id", [], [], {}),
    "products": ("product_id", [], ["standard_cost", "lead_time_days"], {}),
    "suppliers": ("supplier_id", [], ["default_lead_time_days"], {}),
    "facilities": ("facility_id", [], ["capacity"], {}),
    "carriers": ("carrier_id", [], [], {}),
    "supplier_products": ("supplier_product_id", [], [], {"supplier_id": "suppliers", "product_id": "products"}),
    "sales_orders": ("order_id", ["order_date", "required_date"], [], {"customer_id": "customers", "facility_id": "facilities"}),
    "order_lines": ("line_id", [], ["ordered_quantity", "fulfilled_quantity"], {"order_id": "sales_orders", "product_id": "products"}),
    "production": ("production_id", ["production_date"], ["planned_quantity", "produced_quantity"], {"product_id": "products", "facility_id": "facilities"}),
    "inventory": ("inventory_id", ["snapshot_date"], ["opening_quantity", "production_quantity", "receipt_quantity", "consumed_quantity", "on_hand_quantity"], {"product_id": "products", "facility_id": "facilities"}),
    "purchase_orders": ("po_id", ["order_date", "expected_date"], ["ordered_quantity"], {"supplier_id": "suppliers", "product_id": "products", "facility_id": "facilities"}),
    "supplier_deliveries": ("delivery_id", ["delivery_date"], ["delivered_quantity"], {"po_id": "purchase_orders", "supplier_id": "suppliers", "product_id": "products", "facility_id": "facilities"}),
    "shipments": ("shipment_id", ["ship_date", "promised_date", "actual_delivery_date"], ["shipped_quantity", "delivered_quantity"], {"line_id": "order_lines", "order_id": "sales_orders", "carrier_id": "carriers", "product_id": "products", "facility_id": "facilities"}),
}
SOURCES = {
    "customers": "erp", "products": "erp", "sales_orders": "erp", "order_lines": "erp",
    "facilities": "erp", "production": "mes", "inventory": "wms",
    "suppliers": "supplier", "supplier_products": "supplier", "purchase_orders": "supplier",
    "supplier_deliveries": "supplier", "carriers": "logistics", "shipments": "logistics",
}
TEXT_FIELDS = {
    "customers": ["customer_name", "region", "customer_segment"],
    "products": ["product_name", "category", "unit", "seasonal"],
    "suppliers": ["supplier_name", "region", "supplier_tier"],
    "facilities": ["facility_name", "city"], "carriers": ["carrier_name", "mode"],
    "sales_orders": ["status"], "production": ["status"], "purchase_orders": ["status"],
    "shipments": ["route"],
}
