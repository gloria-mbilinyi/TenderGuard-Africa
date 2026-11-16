"""Authenticated browser API tests for PDF workspaces and evaluation."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent import document_workflow
from app.api.browser_auth import reset_browser_sessions_for_tests
from app.api.main import app
from mcp_servers.procurement.tools.document_evaluation import evaluate_document_workspace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCUMENTS = PROJECT_ROOT / "demo_documents"
ORIGIN = "http://127.0.0.1:5173"
PASSWORD = "document-api-test-password"


@pytest.fixture
def client(monkeypatch, tmp_path):
    reset_browser_sessions_for_tests()
    monkeypatch.setenv("TENDERGUARD_DASHBOARD_PASSWORD", PASSWORD)
    monkeypatch.setenv("TENDERGUARD_DOCUMENT_STORAGE", str(tmp_path / "documents"))
    with TestClient(app) as test_client:
        yield test_client
    reset_browser_sessions_for_tests()


def _login(client: TestClient) -> str:
    response = client.post(
        "/api/browser/session",
        json={"password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _create(client: TestClient, csrf: str) -> str:
    response = client.post(
        "/api/browser/document-evaluations",
        json={"title": "API PDF evaluation"},
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    return response.json()["workspace_id"]


def _upload(client: TestClient, csrf: str, workspace_id: str, filename: str, kind: str):
    return client.post(
        f"/api/browser/document-evaluations/{workspace_id}/documents",
        params={"document_type": kind},
        content=(DEMO_DOCUMENTS / filename).read_bytes(),
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf,
            "X-File-Name": filename,
            "Content-Type": "application/pdf",
        },
    )


def test_document_workspace_upload_requires_csrf(client):
    _login(client)
    response = client.post(
        "/api/browser/document-evaluations",
        json={"title": "Missing CSRF"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 403


def test_browser_uploads_three_searchable_pdfs_and_rejects_invalid_content(client):
    csrf = _login(client)
    workspace_id = _create(client, csrf)
    invalid = client.post(
        f"/api/browser/document-evaluations/{workspace_id}/documents",
        params={"document_type": "TENDER_REQUIREMENTS"},
        content=b"not pdf",
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf,
            "X-File-Name": "invalid.pdf",
            "Content-Type": "application/pdf",
        },
    )
    assert invalid.status_code == 400

    for filename, kind in [
        ("tender_requirements_synthetic.pdf", "TENDER_REQUIREMENTS"),
        ("alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
        ("beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
    ]:
        response = _upload(client, csrf, workspace_id, filename, kind)
        assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["status"] == "READY_FOR_EVALUATION"
    assert len(payload["documents"]) == 3
    assert all(item["extracted_preview"] for item in payload["documents"])


def test_document_api_returns_real_evidence_and_null_award(client, monkeypatch):
    csrf = _login(client)
    workspace_id = _create(client, csrf)
    for filename, kind in [
        ("tender_requirements_synthetic.pdf", "TENDER_REQUIREMENTS"),
        ("alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
        ("beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
    ]:
        assert _upload(client, csrf, workspace_id, filename, kind).status_code == 200

    class StubAgent:
        async def ainvoke(self, state):
            assert state["workspace_id"] == workspace_id
            return {
                "status": "AWAITING_HUMAN_REVIEW",
                "completed_tools": [
                    "load_document_workspace",
                    "evaluate_document_workspace",
                ],
                "document_evaluation": evaluate_document_workspace(workspace_id),
                "decision_support": {
                    "review_priority": "ATTENTION_REQUIRED",
                    "summary": "Page-cited evidence prepared for committee review.",
                    "reasons": ["Beta bid contains missing and noncompliant evidence."],
                    "human_committee_required": True,
                    "final_award_decision": None,
                },
            }

    monkeypatch.setattr(document_workflow, "document_procurement_agent", StubAgent())
    response = client.post(
        f"/api/browser/document-evaluations/{workspace_id}/evaluate",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "AWAITING_HUMAN_REVIEW"
    assert result["human_committee_required"] is True
    assert result["final_award_decision"] is None
    assert result["comparison"]["supplier_count"] == 2
    assert result["suppliers"][1]["missing_documents"] == ["REQ-TAX-CLEARANCE"]
    assert result["suppliers"][1]["document_checks"][2]["sources"][0]["page"] == 1

    persisted = client.get(
        f"/api/browser/document-evaluations/{workspace_id}/result"
    )
    assert persisted.status_code == 200
    assert persisted.json()["evaluation_id"] == result["evaluation_id"]
