import hashlib
import json
import shutil
from pathlib import Path
import pandas as pd

EXPORTS = {"executive_kpis": "executive_kpis", "agg_demand": "demand_trends", "agg_inventory": "inventory_health", "agg_supplier": "supplier_scorecard", "agg_logistics": "logistics_performance", "agg_facility": "facility_performance", "forecast_demand": "forecast_demand", "projected_inventory": "projected_inventory", "supply_chain_exception": "supply_chain_exceptions"}


def export(root: Path, tables: dict) -> dict:
    manifest = {}
    for name, frame in tables.items():
        frame.to_csv(root/"data/curated"/f"{name}.csv", index=False, date_format="%Y-%m-%d")
        if name in EXPORTS or name.startswith(("dim_", "fact_", "forecast_")) or name == "bridge_supplier_product":
            dest = root/"outputs/powerbi"/(EXPORTS.get(name, name)+".csv")
            frame.to_csv(dest, index=False, date_format="%Y-%m-%d")
            manifest[dest.name] = {"rows": len(frame), "columns": list(frame.columns), "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
    for name in ("forecast_demand", "forecast_validation", "forecast_test", "forecast_model_metrics", "projected_inventory"):
        tables[name].to_csv(root/"outputs/forecasts"/f"{name}.csv", index=False)
    (root/"outputs/powerbi/manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    from src.config import DEFAULT_ROOT
    for source in ("config/powerbi_theme.json", "config/import_csv.pq", "docs/powerbi_measures.dax"):
        file = DEFAULT_ROOT/source
        if file.exists():
            shutil.copyfile(file, root/"outputs/powerbi"/file.name)
    return manifest
