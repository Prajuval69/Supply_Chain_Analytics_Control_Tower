import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.ai.assistant import answer

@pytest.mark.parametrize("path", ["/health", "/api/executive/summary", "/api/demand/trends", "/api/demand/forecast", "/api/inventory/health", "/api/inventory/risks", "/api/suppliers/scorecard", "/api/logistics/performance", "/api/facilities/performance", "/api/exceptions"])
def test_get_endpoints(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["synthetic_only"]
    if "data" in response.json():
        assert response.json()["total"] > 0 and response.json()["data"]


def test_health_missing_warehouse(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/health")
    assert response.status_code == 503 and "Run python" in response.json()["detail"]


def test_pagination_and_filters(client):
    first = client.get("/api/demand/trends?product_id=1&facility_id=1&limit=2").json()
    second = client.get("/api/demand/trends?product_id=1&facility_id=1&limit=2&offset=2").json()
    assert first["total"] == 18 and len(first["data"]) == 2
    assert first["data"][0]["month"] != second["data"][0]["month"]
    assert all(r["product_id"] == 1 and r["facility_id"] == 1 for r in first["data"])


@pytest.mark.parametrize("query", ["limit=1001", "offset=-1", "product_id=0", "month=nonsense"])
def test_validation_errors(client, query):
    assert client.get("/api/demand/trends?"+query).status_code == 422


def test_no_matches_returns_empty_page(client):
    result = client.get("/api/demand/trends?product_id=99999").json()
    assert result["total"] == 0 and result["data"] == []


def test_sql_injection_is_not_executed(client):
    result = client.get("/api/logistics/performance", params={"route": "'; DROP TABLE dim_product;--"})
    assert result.status_code == 200 and result.json()["total"] == 0
    assert client.get("/api/demand/trends").status_code == 200


def test_exception_get_patch_and_summary(client):
    item = client.get("/api/exceptions?status=Open&limit=1").json()["data"][0]
    path = "/api/exceptions/"+item["exception_id"]
    before = client.get("/api/executive/summary").json()["open_exceptions"]
    try:
        assert client.get(path).json() == item
        assert client.patch(path, json={"status": "Investigating"}).json()["status"] == "Investigating"
        assert client.patch(path, json={"status": "Resolved"}).json()["status"] == "Resolved"
        assert client.get("/api/executive/summary").json()["open_exceptions"] == before-1
        assert client.patch(path, json={"status": "Invalid"}).status_code == 422
    finally:
        client.patch(path, json={"status": item["status"]})


def test_missing_exception(client):
    assert client.get("/api/exceptions/missing").status_code == 404
    assert client.patch("/api/exceptions/missing", json={"status": "Accepted"}).status_code == 404


@pytest.mark.parametrize("question,intent", [("Which products have stockout risk?", "stockout"), ("Which suppliers are underperforming?", "suppliers"), ("Why is OTIF low?", "otif"), ("Which facility has largest backlog?", "backlog"), ("What demand is expected next month?", "forecast"), ("Which products have excess inventory?", "excess"), ("What are critical exceptions?", "exceptions")])
def test_assistant_fallback(client, monkeypatch, question, intent):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    result = client.post("/api/assistant/query", json={"question": question, "use_llm": True})
    assert result.status_code == 200
    body = result.json()
    assert body["mode"] == "deterministic" and body["intent"] == intent
    assert body["evidence"] and body["answer"] and body["synthetic_only"]


def test_assistant_provider_failure_falls_back(db, monkeypatch):
    import httpx
    monkeypatch.setenv("LLM_API_KEY", "test-placeholder")
    def offline(*args, **kwargs):
        raise httpx.ConnectError("Offline test")
    monkeypatch.setattr(httpx, "post", offline)
    response = answer(db, "What demand is expected next month?", use_llm=True)
    assert response["mode"] == "deterministic" and "fallback_reason" in response


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{"message": {"content": ""}}]}])
def test_assistant_malformed_provider_fallback(db, monkeypatch, payload):
    import httpx
    monkeypatch.setenv("LLM_API_KEY", "test-placeholder")
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: httpx.Response(200, json=payload, request=httpx.Request("POST", "https://provider.invalid")))
    result = answer(db, "What demand is expected next month?", True)
    assert result["mode"] == "deterministic" and result["evidence"]


def test_assistant_provider_success_uses_evidence(db, monkeypatch):
    import httpx
    monkeypatch.setenv("LLM_API_KEY", "test-placeholder")
    def fake(*args, **kwargs):
        assert "evidence" in kwargs["json"]["messages"][1]["content"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "Explanation of supplied synthetic evidence."}}]}, request=httpx.Request("POST", "https://provider.invalid"))
    monkeypatch.setattr(httpx, "post", fake)
    assert answer(db, "What demand is expected next month?", True)["mode"] == "llm"


def test_assistant_unknown_question(client):
    body = client.post("/api/assistant/query", json={"question": "Write a poem"}).json()
    assert body["intent"] == "unsupported" and body["evidence"] == []


def test_assistant_rejects_empty_question(client):
    assert client.post("/api/assistant/query", json={"question": ""}).status_code == 422


def test_openapi_has_patch(client):
    schema = client.get("/openapi.json").json()
    assert "patch" in schema["paths"]["/api/exceptions/{exception_id}"]
