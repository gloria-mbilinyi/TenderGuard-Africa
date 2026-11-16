"""Report-library metadata, historical compatibility, and access boundaries."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.browser_auth import reset_browser_sessions_for_tests
from app.api.main import app
from app.api.models import ReportItem
from app.services import reports
from app.services.document_store import (
    add_pdf_document,
    create_workspace,
    save_evaluation_result,
)
from mcp_servers.procurement.tools import generate_document_report
from mcp_servers.procurement.tools.document_evaluation import evaluate_document_workspace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture
def report_environment(monkeypatch, tmp_path):
    output = tmp_path / "reports"
    output.mkdir()
    monkeypatch.setattr(reports, "REPORTS_DIR", output.resolve())
    monkeypatch.setattr(generate_document_report, "REPORTS_DIR", output.resolve())
    monkeypatch.setenv("TENDERGUARD_DOCUMENT_STORAGE", str(tmp_path / "documents"))
    return tmp_path


def _create_report():
    workspace = create_workspace("Report metadata regression test")["workspace_id"]
    for filename, kind in [
        ("tender_requirements_synthetic.pdf", "TENDER_REQUIREMENTS"),
        ("alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
        ("beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
    ]:
        add_pdf_document(
            workspace,
            filename=filename,
            content_type="application/pdf",
            document_type=kind,
            content=(PROJECT_ROOT / "demo_documents" / filename).read_bytes(),
        )
    evidence = evaluate_document_workspace(workspace)
    evidence["tender"]["title"]["value"] = "Supply of regional water pumps"
    for supplier, name in zip(
        evidence["suppliers"], ["Kijani Works Ltd", "Maji Supply Cooperative"], strict=True
    ):
        supplier["supplier_name"]["value"] = name
    evaluation = {
        **evidence,
        "evaluation_id": "report-metadata-evaluation",
        "completed_at": datetime.now(UTC).isoformat(),
        "status": "AWAITING_HUMAN_REVIEW",
        "completed_tools": ["load_document_workspace", "evaluate_document_workspace"],
        "decision_support": {
            "review_priority": "ATTENTION_REQUIRED",
            "summary": "Private evidence summary.",
            "reasons": ["Confidential findings are not library metadata."],
        },
        "human_committee_required": True,
        "final_award_decision": None,
    }
    save_evaluation_result(workspace, evaluation)
    generated = generate_document_report.generate_document_evaluation_report_file(
        workspace, "Named Demo Authorizer"
    )
    return workspace, evaluation, generated


def test_report_uses_validated_saved_evaluation_and_generation_metadata(report_environment):
    workspace, _, generated = _create_report()
    item = ReportItem.model_validate(reports.list_generated_reports()[0]).model_dump()

    assert item["tender_title"] == "Supply of regional water pumps"
    assert item["supplier_names"] == ["Kijani Works Ltd", "Maji Supply Cooperative"]
    assert item["workspace_id"] == workspace
    assert item["generated_at"] == generated["generated_at"]
    assert item["approved_by"] == "Named Demo Authorizer"
    assert item["authorizer_identity_verified"] is False
    assert item["status"] == "DRAFT_FOR_COMMITTEE_REVIEW"
    assert item["download_url"] == f"/api/browser/reports/{workspace}_evaluation_report.md/download"
    serialized = json.dumps(item)
    assert "Private evidence summary" not in serialized
    assert "Confidential findings" not in serialized
    assert "sources" not in item and "report_path" not in item


@pytest.mark.parametrize("failure", ["missing", "corrupt", "invalid", "different_evaluation"])
def test_unavailable_or_mismatched_evaluation_preserves_filename_fallback(
    report_environment, failure
):
    workspace, evaluation, _ = _create_report()
    stored = report_environment / "documents" / workspace / "evaluation.json"
    if failure == "missing":
        stored.rename(stored.with_suffix(".unavailable"))
    elif failure == "corrupt":
        stored.write_text("invalid JSON", encoding="utf-8")
    elif failure == "invalid":
        stored.write_text('{"workspace_id":"invalid"}', encoding="utf-8")
    else:
        evaluation["evaluation_id"] = "a-newer-unrelated-evaluation"
        stored.write_text(json.dumps(evaluation), encoding="utf-8")

    item = ReportItem.model_validate(reports.list_generated_reports()[0])
    assert item.tender_title is None
    assert item.supplier_names == []
    assert item.workspace_id == workspace
    assert reports.resolve_generated_report(item.filename).is_file()


def test_legacy_report_remains_listed_with_optional_metadata(report_environment):
    filename = "BID-LEGACY-001_evaluation_report.md"
    path = reports.REPORTS_DIR / filename
    path.write_text(
        f"# Older draft\n\n{reports.REQUIRED_REPORT_MARKER}\n\nPrivate legacy findings.",
        encoding="utf-8",
    )
    item = ReportItem.model_validate(reports.list_generated_reports()[0])
    assert item.filename == filename
    assert item.tender_title is None and item.supplier_names == []
    assert item.workspace_id is None and item.generated_at is None and item.approved_by is None
    assert reports.resolve_generated_report(filename) == path


def test_legacy_authorization_fields_and_invalid_date_are_handled(report_environment):
    path = reports.REPORTS_DIR / "BID-OLD_evaluation_report.md"
    path.write_text(
        f"{reports.REQUIRED_REPORT_MARKER}\n\n## Human-in-the-Loop Handoff\n\n"
        "Report generation approved by: Legacy Reviewer\n\nGenerated at: invalid-date\n",
        encoding="utf-8",
    )
    item = reports.list_generated_reports()[0]
    assert item["approved_by"] == "Legacy Reviewer"
    assert item["generated_at"] is None


def test_report_metadata_and_download_require_session_and_logout_revokes_access(
    report_environment, monkeypatch
):
    workspace, _, _ = _create_report()
    filename = f"{workspace}_evaluation_report.md"
    monkeypatch.setenv("TENDERGUARD_DASHBOARD_PASSWORD", "test-report-library-password")
    reset_browser_sessions_for_tests()
    with TestClient(app) as client:
        assert client.get("/api/browser/reports").status_code == 401
        assert client.get(f"/api/browser/reports/{filename}/download").status_code == 401
        login = client.post(
            "/api/browser/session",
            headers={"Origin": ORIGIN},
            json={"password": "test-report-library-password"},
        )
        assert login.status_code == 200
        response = client.get("/api/browser/reports")
        assert response.status_code == 200
        payload = response.json()
        assert payload["approval_available_in_browser"] is False
        item = payload["reports"][0]
        assert item["tender_title"] == "Supply of regional water pumps"
        assert "Private evidence summary" not in response.text
        assert client.get(item["download_url"]).status_code == 200
        assert client.get("/api/browser/reports/audit_log.jsonl/download").status_code == 404
        assert (
            client.post(
                "/api/browser/logout",
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": login.json()["csrf_token"],
                },
            ).status_code
            == 204
        )
        assert client.get("/api/browser/reports").status_code == 401
        assert client.get(item["download_url"]).status_code == 401
    reset_browser_sessions_for_tests()


def test_report_library_rejects_out_of_directory_symlinks(report_environment):
    outside = report_environment / "private.md"
    outside.write_text(reports.REQUIRED_REPORT_MARKER, encoding="utf-8")
    link = reports.REPORTS_DIR / "BID-LINK_evaluation_report.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is unavailable on this Windows configuration.")
    assert reports.list_generated_reports() == []
    with pytest.raises(FileNotFoundError):
        reports.resolve_generated_report(link.name)
