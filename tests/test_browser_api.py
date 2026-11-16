"""Authenticated browser API tests; no network or Ollama required."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.browser_auth import reset_browser_sessions_for_tests
from app.api.main import app
from app.services.evaluation_store import reset_evaluations_for_tests
from mcp_servers.procurement.tools.check_bid_compliance import check_bid_compliance_record
from mcp_servers.procurement.tools.compare_prices import compare_bid_price
from mcp_servers.procurement.tools.flag_supplier_risk import flag_supplier_risk_record
from mcp_servers.procurement.tools.load_tender import load_tender_record

ORIGIN = "http://127.0.0.1:5173"
DASHBOARD_PASSWORD = "test-dashboard-password"


@pytest.fixture(autouse=True)
def clean_browser_state(monkeypatch):
    reset_browser_sessions_for_tests()
    reset_evaluations_for_tests()
    monkeypatch.setenv("TENDERGUARD_DASHBOARD_PASSWORD", DASHBOARD_PASSWORD)
    yield
    reset_browser_sessions_for_tests()
    reset_evaluations_for_tests()


@pytest.fixture
def browser_client():
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/browser/session",
        json={"password": DASHBOARD_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def _stub_agent(monkeypatch, state):
    class StubAgent:
        async def ainvoke(self, request):
            assert request == {
                "tender_id": "TG-DEMO-001",
                "bid_id": "BID-ALPHA-001",
                "status": "STARTED",
            }
            return state

    monkeypatch.setitem(
        sys.modules,
        "app.agent.workflow",
        SimpleNamespace(procurement_agent=StubAgent()),
    )


def _complete_state():
    return {
        "status": "AWAITING_HUMAN_REVIEW",
        "completed_tools": [
            "load_tender",
            "check_bid_compliance",
            "compare_prices",
            "flag_supplier_risk",
        ],
        "tender": load_tender_record("TG-DEMO-001"),
        "compliance": check_bid_compliance_record("TG-DEMO-001", "BID-ALPHA-001"),
        "price_analysis": compare_bid_price("BID-ALPHA-001"),
        "supplier_risk": flag_supplier_risk_record("BID-ALPHA-001"),
        "decision_support": {
            "review_priority": "STANDARD_REVIEW",
            "summary": "Evidence package prepared for human committee review.",
            "reasons": ["Mandatory checks passed in the synthetic source records."],
            "human_committee_required": True,
            "final_award_decision": None,
        },
    }


def test_browser_routes_require_a_session(browser_client):
    assert browser_client.get("/api/browser/catalog").status_code == 401
    assert browser_client.get("/api/browser/evaluations").status_code == 401
    assert browser_client.get("/api/browser/reports").status_code == 401


def test_login_requires_configuration_and_allowed_origin(browser_client, monkeypatch):
    monkeypatch.delenv("TENDERGUARD_DASHBOARD_PASSWORD")
    response = browser_client.post(
        "/api/browser/session",
        json={"password": DASHBOARD_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 503

    monkeypatch.setenv("TENDERGUARD_DASHBOARD_PASSWORD", DASHBOARD_PASSWORD)
    assert browser_client.post(
        "/api/browser/session",
        json={"password": DASHBOARD_PASSWORD},
        headers={"Origin": "https://attacker.invalid"},
    ).status_code == 403
    assert browser_client.post(
        "/api/browser/session",
        json={"password": "incorrect-password"},
        headers={"Origin": ORIGIN},
    ).status_code == 401


def test_login_uses_httponly_strict_cookie_without_exposing_credentials(browser_client):
    response = browser_client.post(
        "/api/browser/session",
        json={"password": DASHBOARD_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api/browser" in set_cookie
    payload = response.json()
    assert "session" not in payload
    assert DASHBOARD_PASSWORD not in response.text
    assert payload["auth_mode"] == "LOCAL_DEMO_SESSION"


def test_catalog_contains_only_synthetic_demo_records(browser_client):
    _login(browser_client)
    response = browser_client.get("/api/browser/catalog")
    assert response.status_code == 200
    tender = response.json()["tenders"][0]
    assert tender["tender_id"] == "TG-DEMO-001"
    assert tender["synthetic"] is True
    assert {bid["bid_id"] for bid in tender["bids"]} == {
        "BID-ALPHA-001",
        "BID-BETA-001",
    }
    assert all(bid["synthetic"] is True for bid in tender["bids"])


def test_evaluation_requires_csrf_and_returns_validated_evidence(
    browser_client,
    monkeypatch,
):
    csrf_token = _login(browser_client)
    request = {"tender_id": "TG-DEMO-001", "bid_id": "BID-ALPHA-001"}
    assert browser_client.post(
        "/api/browser/evaluations",
        json=request,
        headers={"Origin": ORIGIN},
    ).status_code == 403

    _stub_agent(monkeypatch, _complete_state())
    response = browser_client.post(
        "/api/browser/evaluations",
        json=request,
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "AWAITING_HUMAN_REVIEW"
    assert payload["human_committee_required"] is True
    assert payload["final_award_decision"] is None
    assert payload["decision_support"]["final_award_decision"] is None
    assert payload["compliance"]["source_files"]
    assert payload["price_analysis"]["sources"]
    assert payload["supplier_risk"]["source_files"]

    stored = browser_client.get("/api/browser/evaluations").json()["evaluations"]
    assert len(stored) == 1
    assert stored[0]["evaluation_id"] == payload["evaluation_id"]
    assert stored[0]["final_award_decision"] is None


def test_browser_evaluation_rejects_unavailable_bid(browser_client):
    csrf_token = _login(browser_client)
    response = browser_client.post(
        "/api/browser/evaluations",
        json={"tender_id": "TG-DEMO-001", "bid_id": "BID-UNKNOWN"},
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 404


def test_report_library_only_lists_and_downloads_generated_drafts(
    browser_client,
    monkeypatch,
    tmp_path: Path,
):
    from app.services import reports as reports_service

    monkeypatch.setattr(reports_service, "REPORTS_DIR", tmp_path.resolve())
    valid = tmp_path / "BID-ALPHA-001_evaluation_report.md"
    valid.write_text(
        "# DRAFT FOR HUMAN PROCUREMENT COMMITTEE REVIEW\n\nSynthetic report.",
        encoding="utf-8",
    )
    (tmp_path / "audit.jsonl").write_text('{"event":"private"}', encoding="utf-8")
    (tmp_path / "BID-BETA-001_evaluation_report.md").write_text(
        "Not a generated committee draft.",
        encoding="utf-8",
    )

    _login(browser_client)
    response = browser_client.get("/api/browser/reports")
    assert response.status_code == 200
    payload = response.json()
    assert payload["approval_available_in_browser"] is False
    assert [item["filename"] for item in payload["reports"]] == [valid.name]

    download = browser_client.get(payload["reports"][0]["download_url"])
    assert download.status_code == 200
    assert "Synthetic report" in download.text
    assert browser_client.get("/api/browser/reports/audit.jsonl/download").status_code == 404


def test_logout_revokes_session(browser_client):
    csrf_token = _login(browser_client)
    response = browser_client.post(
        "/api/browser/logout",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 204
    assert browser_client.get("/api/browser/catalog").status_code == 401
