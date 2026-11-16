"""API security and workflow-contract tests; no network or Ollama needed."""

import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)


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


def test_health_does_not_require_api_key(monkeypatch):
    monkeypatch.delenv("TENDERGUARD_API_KEY", raising=False)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_evaluation_requires_configured_key(monkeypatch):
    monkeypatch.delenv("TENDERGUARD_API_KEY", raising=False)
    response = client.post("/api/evaluations", json={"tender_id": "TG-1", "bid_id": "BID-1"})
    assert response.status_code == 503


def test_evaluation_rejects_missing_or_invalid_key(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", "secret-test-key")
    data = {"tender_id": "TG-1", "bid_id": "BID-1"}
    assert client.post("/api/evaluations", json=data).status_code == 401
    assert client.post(
        "/api/evaluations", json=data, headers={"X-TenderGuard-Key": "wrong"}
    ).status_code == 401


def test_evaluation_returns_only_human_review(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", "secret-test-key")
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
        json={"tender_id": "TG-1", "bid_id": "BID-1"},
        headers={"X-TenderGuard-Key": "secret-test-key"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "AWAITING_HUMAN_REVIEW"
    assert result["human_committee_required"] is True
    assert result["final_award_decision"] is None
    assert result["decision_support"]["final_award_decision"] is None


def test_evaluation_refuses_automatic_award(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", "secret-test-key")
    _stub_agent(
        monkeypatch,
        {
            "status": "AWAITING_HUMAN_REVIEW",
            "decision_support": {"final_award_decision": "BID-1"},
        },
    )
    response = client.post(
        "/api/evaluations",
        json={"tender_id": "TG-1", "bid_id": "BID-1"},
        headers={"X-TenderGuard-Key": "secret-test-key"},
    )
    assert response.status_code == 500


def test_evaluation_blocks_invalid_identifiers(monkeypatch):
    monkeypatch.setenv("TENDERGUARD_API_KEY", "secret-test-key")
    response = client.post(
        "/api/evaluations",
        json={"tender_id": "../private", "bid_id": "BID-1"},
        headers={"X-TenderGuard-Key": "secret-test-key"},
    )
    assert response.status_code == 422
