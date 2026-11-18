// Save as fnPackRightCsv. DataFolder is a text parameter pointing to outputs/powerbi.
// Example query: fnPackRightCsv(DataFolder, "demand_trends")
(DataFolder as text, Dataset as text) as table =>
let
    Folder = Text.TrimEnd(DataFolder, {"/", "\"}),
    Source = Csv.Document(File.Contents(Folder & "/" & Dataset & ".csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    DateNames = {"date", "month", "month_start", "as_of", "order_date", "required_date",
        "production_date", "snapshot_date", "expected_date", "delivery_date", "ship_date",
        "promised_date", "actual_delivery_date", "forecast_date", "train_end", "stockout_date", "detected_date"},
    KeyNames = {"customer_id", "product_id", "supplier_id", "facility_id", "carrier_id", "date_id",
        "line_id", "order_id", "production_id", "inventory_id", "po_id", "delivery_id", "shipment_id",
        "supplier_product_id", "horizon", "year", "quarter", "seasonal", "selected"},
    NumericNames = {"prediction", "actual", "mae", "rmse", "mape", "mape_eligible_count", "capacity",
        "standard_cost", "lead_time_days", "default_lead_time_days", "delay_days", "on_time", "in_full", "otif",
        "deliveries", "otif_count", "on_time_count", "late_count", "average_lead_time", "lead_time_variance",
        "supplier_otif", "late_delivery_rate", "fill_rate", "shipments", "logistics_otif", "late_shipment_rate",
        "average_delivery_delay", "demand_growth", "demand_volatility", "previous_demand", "average_inventory",
        "stockout_count", "average_daily_demand", "days_of_inventory", "current_days_of_inventory", "inventory_value",
        "average_inventory_value", "synthetic_cogs_proxy", "inventory_turnover", "excess_inventory", "production_attainment",
        "latest_production", "latest_planned", "latest_production_attainment", "order_count", "fulfilled_orders",
        "open_orders", "overdue_orders", "fulfillment_rate", "exceptions", "history_days", "total_demand",
        "average_inventory_quantity", "shipment_count", "excess_inventory_pairs", "stockout_risk_pairs", "open_exceptions",
        "opening_inventory", "expected_receipts", "forecast_demand", "projected_ending_inventory", "stockout_flag",
        "excess_inventory_flag", "threshold", "actual_value", "expected_value"},
    Names = Table.ColumnNames(Headers),
    Types = List.Transform(Names, (n) => {n,
        if List.Contains(DateNames, n) and not (n="month" and Dataset="dim_date") then type date
        else if List.Contains(KeyNames,n) or (n="month" and Dataset="dim_date") then Int64.Type
        else if List.Contains(NumericNames,n) or Text.EndsWith(n,"_quantity") then type number
        else type text}),
    BlanksAsNull = Table.ReplaceValue(Headers,"",null,Replacer.ReplaceValue,Names),
    Typed = Table.TransformColumnTypes(BlanksAsNull, Types, "en-US")
in
    Typed
