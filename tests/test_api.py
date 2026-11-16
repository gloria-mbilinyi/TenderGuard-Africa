"""API security and workflow-contract tests; no network or Ollama needed."""

import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agent.ollama_client import OllamaUnavailableError
from app.api.main import app

client = TestClient(app)
TEST_API_KEY = "test-key-0123456789abcdef0123456789abcdef"


def _stub_agent(monkeypatch, state):
    class StubAgent:
        async def ainvoke(self, request):
            assert request["status"] == "STARTED"
            return state

    monkeypatch.setitem(
        sys.modules,
        "app.agent.workflow",
        SimpleNamespace(procurement_agent=StubAgent()),
    )


def _stub_failing_agent(monkeypatch, error):
    class StubAgent:
        async def ainvoke(self, request):
            raise error

    monkeypatch.setitem(
        sys.modules,
        "app.agent.workflow",
        SimpleNamespace(procurement_agent=StubAgent()),
    )


def test_health_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("TENDERGUARD_API_KEY", raising=False)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_evaluation_requires_configured_key(monkeypatch):
    monkeypatch.delenv("TENDERGUARD_API_KEY", raising=False)
    response = client.post("/api/evaluations", json={"tender_id": "TG-1", "bid_id": "BID-1"})
    assert response.status_code == 503


def test_evaluation_rejects_short_configured_key(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", "too-short")
    response = client.post("/api/evaluations", json={"tender_id": "TG-1", "bid_id": "BID-1"})
    assert response.status_code == 503


def test_evaluation_rejects_missing_or_invalid_key(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", TEST_API_KEY)
    data = {"tender_id": "TG-1", "bid_id": "BID-1"}
    assert client.post("/api/evaluations", json=data).status_code == 401
    assert client.post(
        "/api/evaluations", json=data, headers={"X-TenderGuard-Key": "wrong"}
    ).status_code == 401


def test_evaluation_returns_only_human_review(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", TEST_API_KEY)
    _stub_agent(
        monkeypatch,
        {
            "status": "AWAITING_HUMAN_REVIEW",
            "completed_tools": ["load_tender", "check_bid_compliance"],
            "decision_support": {"summary": "Mocked evaluation", "review_priority": "STANDARD_REVIEW"},
        },
    )
    response = client.post(
        "/api/evaluations",
        json={"tender_id": "TG-DEMO-001", "bid_id": "BID-ALPHA-001"},
        headers={"X-TenderGuard-Key": TEST_API_KEY},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "AWAITING_HUMAN_REVIEW"
    assert result["human_committee_required"] is True
    assert result["final_award_decision"] is None
    assert result["decision_support"]["final_award_decision"] is None


def test_evaluation_refuses_automatic_award(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", TEST_API_KEY)
    _stub_agent(
        monkeypatch,
        {
            "status": "AWAITING_HUMAN_REVIEW",
            "decision_support": {"final_award_decision": "BID-ALPHA-001"},
        },
    )
    response = client.post(
        "/api/evaluations",
        json={"tender_id": "TG-DEMO-001", "bid_id": "BID-ALPHA-001"},
        headers={"X-TenderGuard-Key": TEST_API_KEY},
    )
    assert response.status_code == 502


def test_evaluation_blocks_invalid_identifiers(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", TEST_API_KEY)
    response = client.post(
        "/api/evaluations",
        json={"tender_id": "../private", "bid_id": "BID-1"},
        headers={"X-TenderGuard-Key": TEST_API_KEY},
    )
    assert response.status_code == 422


def test_evaluation_reports_clear_ollama_error(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", TEST_API_KEY)
    _stub_failing_agent(
        monkeypatch,
        OllamaUnavailableError("Ollama is unavailable; start it and pull qwen3:1.7b."),
    )
    response = client.post(
        "/api/evaluations",
        json={"tender_id": "TG-DEMO-001", "bid_id": "BID-ALPHA-001"},
        headers={"X-TenderGuard-Key": TEST_API_KEY},
    )
    assert response.status_code == 503
    assert "Ollama is unavailable" in response.json()["detail"]


def test_evaluation_rejects_unknown_catalog_selection(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", TEST_API_KEY)
    response = client.post(
        "/api/evaluations",
        json={"tender_id": "TG-UNKNOWN", "bid_id": "BID-UNKNOWN"},
        headers={"X-TenderGuard-Key": TEST_API_KEY},
    )
    assert response.status_code == 404
    assert "not available" in response.json()["detail"]
