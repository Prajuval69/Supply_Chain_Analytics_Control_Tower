import sqlite3
from contextlib import closing
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from src.config import settings
from src.pipeline.run import run
from src.api.app import create_app


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("packright")
    cfg = settings()
    cfg.update(customers=30, products=20, suppliers=14, carriers=5, months=18, orders_per_month=40, purchase_orders_per_month=30)
    report = run(root, cfg=cfg)
    return root, cfg, report


@pytest.fixture
def db(built):
    with closing(sqlite3.connect(built[0]/"database/control_tower.sqlite")) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn


@pytest.fixture
def client(built):
    with TestClient(create_app(built[0])) as client:
        yield client


@pytest.fixture
def clean_tables(built):
    from src.data.contracts import CONTRACTS
    tables = {}
    for name, (_, dates, _, _) in CONTRACTS.items():
        tables[name] = pd.read_csv(built[0]/"data/processed"/f"{name}.csv", parse_dates=dates)
    return tables
