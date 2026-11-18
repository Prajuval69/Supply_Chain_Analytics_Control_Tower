"""Repeat the full pipeline and prove row/hash idempotency."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from src.config import root_path
from src.pipeline.run import run


def verify(root=None):
    root = root or root_path()
    manifest_file = root/"outputs/powerbi/manifest.json"
    before = json.loads(manifest_file.read_text())
    prior = json.loads((root/"outputs/reports/run_summary.json").read_text())
    result = run(root, regenerate=False)
    after = json.loads(manifest_file.read_text())
    assert before == after, "Reporting hashes changed on identical inputs"
    assert result["record_counts"] == prior["record_counts"], "Warehouse counts changed"
    receipt = {"executed_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(), "identical_hashes": True, "identical_record_counts": True, "files_compared": len(before), "record_counts": result["record_counts"]}
    (root/"outputs/reports/idempotency.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Full-size rerun: {len(before)} identical CSV hashes and all warehouse counts unchanged")
    return receipt


if __name__ == "__main__":
    verify()
