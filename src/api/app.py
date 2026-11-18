import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from src.config import root_path
from src.ai.assistant import answer


class DataPage(BaseModel):
    data: list[dict]
    total: int
    limit: int
    offset: int
    synthetic_only: bool = True


class StatusUpdate(BaseModel):
    status: Literal["Open", "Investigating", "Resolved", "Accepted"]


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    use_llm: bool = False


def create_app(root: Path | None = None):
    app = FastAPI(title="PackRight Supply Chain Control Tower", version="1.0.0", description="Fictional, synthetic data only. Snapshot dates are independent of server time.")
    @contextmanager
    def connection():
        path = (root or root_path())/"database/control_tower.sqlite"
        if not path.is_file():
            raise HTTPException(503, "Warehouse unavailable. Run python -m src.pipeline.run first.")
        try:
            db = sqlite3.connect(path, timeout=5)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            yield db
        except sqlite3.Error as exc:
            raise HTTPException(503, "Warehouse query failed; inspect local pipeline/database logs.") from exc
        finally:
            if "db" in locals():
                db.close()

    def page(table, filters, limit, offset, ordering, extra="1=1"):
        clauses, params = [extra], []
        for key, value in filters.items():
            if value is not None:
                clauses.append(f'"{key}" = ?')
                params.append(value)
        where = " AND ".join(clauses)
        with connection() as db:
            total = db.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]
            data = [dict(r) for r in db.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY {ordering} LIMIT ? OFFSET ?", [*params, limit, offset])]
        return DataPage(data=data, total=total, limit=limit, offset=offset)

    @app.get("/", include_in_schema=False)
    def index():
        return RedirectResponse("/docs")

    @app.get("/health")
    def health():
        with connection() as db:
            row = db.execute("SELECT as_of FROM executive_kpis").fetchone()
            if not row:
                raise HTTPException(503, "Warehouse is empty")
            return {"status": "ok", "database": "ready", "as_of": row[0], "synthetic_only": True}

    @app.get("/api/executive/summary")
    def executive():
        with connection() as db:
            row = db.execute("SELECT * FROM executive_kpis").fetchone()
            if not row:
                raise HTTPException(503, "Executive snapshot unavailable")
            result = dict(row)
            result["open_exceptions"] = db.execute("SELECT COUNT(*) FROM supply_chain_exception WHERE status IN ('Open','Investigating')").fetchone()[0]
            result["synthetic_only"] = True
            return result

    @app.get("/api/demand/trends", response_model=DataPage)
    def trends(product_id: int | None = Query(None, ge=1), facility_id: int | None = Query(None, ge=1), month: date | None = None, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return page("agg_demand", {"product_id": product_id, "facility_id": facility_id, "month": month.isoformat() if month else None}, limit, offset, "month,product_id,facility_id")

    @app.get("/api/demand/forecast", response_model=DataPage)
    def forecasts(product_id: int | None = Query(None, ge=1), horizon: int | None = Query(None, ge=1, le=3), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return page("forecast_demand", {"product_id": product_id, "horizon": horizon}, limit, offset, "product_id,horizon")

    @app.get("/api/inventory/health", response_model=DataPage)
    def inventory(product_id: int | None = Query(None, ge=1), facility_id: int | None = Query(None, ge=1), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return page("agg_inventory", {"product_id": product_id, "facility_id": facility_id}, limit, offset, "facility_id,product_id")

    @app.get("/api/inventory/risks", response_model=DataPage)
    def risks(product_id: int | None = Query(None, ge=1), facility_id: int | None = Query(None, ge=1), risk_type: Literal["stockout", "excess", "all"] = "all", horizon: int | None = Query(None, ge=1, le=3), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        predicate = {"stockout": "stockout_flag=1", "excess": "excess_inventory_flag=1", "all": "(stockout_flag=1 OR excess_inventory_flag=1)"}[risk_type]
        return page("projected_inventory", {"product_id": product_id, "facility_id": facility_id, "horizon": horizon}, limit, offset, "horizon,projected_ending_inventory,product_id,facility_id", predicate)

    @app.get("/api/suppliers/scorecard", response_model=DataPage)
    def suppliers(supplier_id: int | None = Query(None, ge=1), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return page("agg_supplier", {"supplier_id": supplier_id}, limit, offset, "supplier_otif,supplier_id")

    @app.get("/api/logistics/performance", response_model=DataPage)
    def logistics(carrier_id: int | None = Query(None, ge=1), facility_id: int | None = Query(None, ge=1), route: str | None = Query(None, max_length=100), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return page("agg_logistics", {"carrier_id": carrier_id, "facility_id": facility_id, "route": route}, limit, offset, "carrier_id,facility_id,route")

    @app.get("/api/facilities/performance", response_model=DataPage)
    def facilities(facility_id: int | None = Query(None, ge=1), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        result = page("agg_facility", {"facility_id": facility_id}, limit, offset, "facility_id")
        with connection() as db:
            for row in result.data:
                row["open_exceptions"] = db.execute("SELECT COUNT(*) FROM supply_chain_exception WHERE facility_id=? AND status IN ('Open','Investigating')", (row["facility_id"],)).fetchone()[0]
        return result

    @app.get("/api/exceptions", response_model=DataPage)
    def exceptions(status: Literal["Open", "Investigating", "Resolved", "Accepted"] | None = None, severity: Literal["Critical", "High", "Medium", "Low"] | None = None, type: Literal["STOCKOUT_RISK", "EXCESS_INVENTORY", "SUPPLIER_DELAY", "SHIPMENT_DELAY", "ORDER_BACKLOG", "LOW_SUPPLIER_OTIF", "HIGH_DEMAND_VOLATILITY", "PRODUCTION_SHORTFALL"] | None = None, facility_id: int | None = Query(None, ge=1), product_id: int | None = Query(None, ge=1), supplier_id: int | None = Query(None, ge=1), limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        return page("supply_chain_exception", {"status": status, "severity": severity, "type": type, "facility_id": facility_id, "product_id": product_id, "supplier_id": supplier_id}, limit, offset, "CASE severity WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,exception_id")

    @app.get("/api/exceptions/{exception_id}")
    def exception(exception_id: str):
        with connection() as db:
            row = db.execute("SELECT * FROM supply_chain_exception WHERE exception_id=?", (exception_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Exception not found")
            return dict(row)

    @app.patch("/api/exceptions/{exception_id}")
    def patch_exception(exception_id: str, update: StatusUpdate):
        with connection() as db:
            cursor = db.execute("UPDATE supply_chain_exception SET status=? WHERE exception_id=?", (update.status, exception_id))
            if cursor.rowcount == 0:
                raise HTTPException(404, "Exception not found")
            db.commit()
        return exception(exception_id)

    @app.post("/api/assistant/query")
    def assistant(request: AssistantRequest):
        with connection() as db:
            return answer(db, request.question, request.use_llm)

    return app


app = create_app()
