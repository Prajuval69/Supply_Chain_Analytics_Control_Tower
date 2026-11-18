"""Portable configuration. Business time is the final synthetic history date."""
import json
import os
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def root_path() -> Path:
    return Path(os.environ.get("PACKRIGHT_ROOT") or DEFAULT_ROOT).resolve()


def settings(root: Path | None = None) -> dict:
    root = root or root_path()
    file = root / "config/settings.json"
    if not file.exists():
        file = DEFAULT_ROOT / "config/settings.json"
    config = json.loads(file.read_text(encoding="utf-8"))
    if config["months"] < 18 or not 1 <= config["forecast_horizon"] <= 3:
        raise ValueError("Require >=18 history months and 1-3 forecast months")
    return config


def prepare(root: Path) -> None:
    for folder in ("data/raw", "data/staging", "data/processed", "data/curated",
                   "data/reference", "database", "outputs/powerbi", "outputs/reports",
                   "outputs/forecasts", "logs"):
        (root / folder).mkdir(parents=True, exist_ok=True)

