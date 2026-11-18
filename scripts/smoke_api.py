"""Real HTTP smoke tests against a separately running uvicorn process."""
import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from src.config import root_path


def smoke(base_url):
    results = []
    paths = ["/health", "/api/executive/summary", "/api/demand/trends", "/api/demand/forecast", "/api/inventory/health", "/api/inventory/risks", "/api/suppliers/scorecard", "/api/logistics/performance", "/api/facilities/performance", "/api/exceptions"]
    with httpx.Client(base_url=base_url, timeout=15) as client:
        for path in paths:
            response = client.get(path)
            response.raise_for_status()
            body = response.json()
            assert body["synthetic_only"]
            if "data" in body:
                assert body["total"] > 0 and body["data"]
            results.append({"method": "GET", "path": path, "status": response.status_code, "rows": len(body.get("data", []))})
        eid = client.get("/api/exceptions?limit=1").json()["data"][0]["exception_id"]
        path = "/api/exceptions/"+eid
        response = client.get(path)
        response.raise_for_status()
        old_status = response.json()["status"]
        results.append({"method": "GET", "path": path, "status": response.status_code})
        try:
            response = client.patch(path, json={"status": "Investigating"})
            response.raise_for_status()
            assert response.json()["status"] == "Investigating"
            assert client.get(path).json()["status"] == "Investigating"
            results.append({"method": "PATCH", "path": path, "status": response.status_code, "persisted": True})
        finally:
            response = client.patch(path, json={"status": old_status})
            response.raise_for_status()
        response = client.post("/api/assistant/query", json={"question": "Which products have stockout risk?"})
        response.raise_for_status()
        assert response.json()["mode"] == "deterministic" and response.json()["evidence"]
        results.append({"method": "POST", "path": "/api/assistant/query", "status": response.status_code, "mode": response.json()["mode"]})
        for path, expected in [("/api/exceptions/missing", 404), ("/api/demand/trends?limit=1001", 422)]:
            response = client.get(path)
            assert response.status_code == expected
            results.append({"method": "GET", "path": path, "status": response.status_code, "expected_error": True})
    report = {"executed_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(), "base_url": base_url, "transport": "real HTTP against uvicorn", "checks": results, "passed": len(results)}
    dest = root_path()/"outputs/reports/api_smoke.json"
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    smoke(parser.parse_args().base_url)
