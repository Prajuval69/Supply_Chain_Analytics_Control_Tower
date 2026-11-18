"""python -m src.pipeline.run [--skip-generate] [--root PATH]."""
import argparse
import json
import logging
from pathlib import Path
from time import perf_counter
from src.config import prepare, root_path, settings
from src.data.generate import generate
from src.pipeline.clean import ingest_clean, curate
from src.analytics.metrics import calculate
from src.forecasting.models import forecast, error_metrics
from src.inventory.project import projections
from src.exceptions.engine import generate_exceptions
from src.db.warehouse import load, previous_statuses
from src.reporting.export import export


def run(root: Path | None = None, regenerate=True, cfg=None) -> dict:
    root = Path(root or root_path()).resolve()
    prepare(root)
    cfg = cfg or settings(root)
    start = perf_counter()
    logger = logging.getLogger("packright")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(root/"logs/pipeline.log", encoding="utf-8")
    logger.addHandler(handler)
    stages = []
    def record(message):
        stages.append(message)
        logger.info(message)
        print(message, flush=True)
    try:
        if regenerate:
            generate(root, cfg)
            record("Generated synthetic source data")
        cleaned, quality = ingest_clean(root)
        record("Ingested, profiled, standardized and quarantined source records")
        curated = curate(cleaned)
        analytics = calculate(curated, cfg)
        record("Curated star schema and calculated all domain KPIs")
        future, validation, model_metrics, holdout = forecast(analytics["agg_demand"], cfg["forecast_horizon"])
        projected = projections(analytics, curated, future, cfg)
        previous = previous_statuses(root/"database/control_tower.sqlite")
        exceptions = generate_exceptions(curated, analytics, projected, cfg, previous)
        analytics["agg_facility"]["exceptions"] = analytics["agg_facility"].facility_id.map(exceptions.groupby("facility_id").size()).fillna(0).astype(int)
        analytics["executive_kpis"]["stockout_risk_pairs"] = len(projected.loc[projected.stockout_flag == 1, ["product_id", "facility_id"]].drop_duplicates())
        analytics["executive_kpis"]["open_exceptions"] = int(exceptions.status.isin(["Open", "Investigating"]).sum())
        tables = {**curated, **analytics, "forecast_demand": future, "forecast_validation": validation, "forecast_model_metrics": model_metrics, "forecast_test": holdout, "projected_inventory": projected, "supply_chain_exception": exceptions}
        record("Evaluated forecasts, projected inventory and generated exceptions")
        db_report = load(root, tables)
        manifest = export(root, tables)
        record("Loaded and validated SQLite; exported Power BI and forecast datasets")
        selected = validation.merge(model_metrics[model_metrics.selected == 1][["product_id", "model_name"]], on=["product_id", "model_name"])
        forecast_report = {"selected_model_counts": future[future.horizon == 1].model_name.value_counts().to_dict(), "selected_validation_metrics": error_metrics(selected.actual, selected.prediction), "untouched_test_metrics": error_metrics(holdout.actual, holdout.prediction), "candidate_validation_metrics": {m: error_metrics(g.actual, g.prediction) for m, g in validation.groupby("model_name")}}
        report = {"synthetic_only": True, "configuration": cfg, "as_of": str(curated["fact_inventory"].snapshot_date.max().date()), "stages": stages, "duration_seconds": round(perf_counter()-start, 3), "record_counts": db_report["record_counts"], "raw_counts": {n: r["raw"]["rows"] for n, r in quality.items()}, "cleaned_counts": {n: r["cleaned"]["rows"] for n, r in quality.items()}, "rejected_rows": sum(r["rejected_rows"] for r in quality.values()), "kpis": analytics["executive_kpis"].iloc[0].to_dict(), "forecast": forecast_report, "exception_counts": exceptions.type.value_counts().to_dict(), "severity_counts": exceptions.severity.value_counts().to_dict(), "database": db_report, "powerbi_files": manifest}
        (root/"outputs/reports/run_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        logger.info("Run complete: %s", json.dumps({"seconds": report["duration_seconds"], "exceptions": len(exceptions)}))
        return report
    finally:
        logger.removeHandler(handler)
        handler.close()


def main():
    parser = argparse.ArgumentParser(description="PackRight synthetic analytics pipeline")
    parser.add_argument("--root", type=Path, default=root_path())
    parser.add_argument("--skip-generate", action="store_true", help="Process existing raw files")
    args = parser.parse_args()
    report = run(args.root, not args.skip_generate)
    print(json.dumps({"as_of": report["as_of"], "kpis": report["kpis"], "forecast": report["forecast"], "exceptions": report["exception_counts"]}, indent=2))


if __name__ == "__main__":
    main()
