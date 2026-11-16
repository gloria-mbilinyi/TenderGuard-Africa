"""Human-authorized report generation for uploaded document evaluations."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.document_store import (
    add_pdf_document,
    create_workspace,
    save_evaluation_result,
)
from mcp_servers.procurement.tools.document_evaluation import evaluate_document_workspace
from mcp_servers.procurement.tools.generate_document_report import (
    generate_document_evaluation_report_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCUMENTS = PROJECT_ROOT / "demo_documents"


def test_document_report_requires_named_human_and_preserves_null_award(
    monkeypatch, tmp_path
):
    from mcp_servers.procurement.tools import generate_document_report

    monkeypatch.setenv("TENDERGUARD_DOCUMENT_STORAGE", str(tmp_path / "documents"))
    monkeypatch.setattr(generate_document_report, "REPORTS_DIR", tmp_path / "reports")
    workspace_id = create_workspace("Report test")["workspace_id"]
    for filename, document_type in [
        ("tender_requirements_synthetic.pdf", "TENDER_REQUIREMENTS"),
        ("alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
        ("beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
    ]:
        add_pdf_document(
            workspace_id,
            filename=filename,
            content_type="application/pdf",
            document_type=document_type,
            content=(DEMO_DOCUMENTS / filename).read_bytes(),
        )
    evidence = evaluate_document_workspace(workspace_id)
    result = {
        "evaluation_id": "test-document-evaluation",
        "workspace_id": workspace_id,
        "completed_at": datetime.now(UTC).isoformat(),
        "status": "AWAITING_HUMAN_REVIEW",
        "completed_tools": ["load_document_workspace", "evaluate_document_workspace"],
        **evidence,
        "decision_support": {
            "review_priority": "ATTENTION_REQUIRED",
            "summary": "Evidence prepared for human review.",
            "reasons": ["Beta evidence requires attention."],
            "human_committee_required": True,
            "final_award_decision": None,
        },
        "human_committee_required": True,
        "final_award_decision": None,
    }
    save_evaluation_result(workspace_id, result)

    with pytest.raises(PermissionError, match="Named human approval"):
        generate_document_evaluation_report_file(workspace_id, "")

    generated = generate_document_evaluation_report_file(
        workspace_id, "Synthetic Demo Reviewer"
    )
    report_path = tmp_path / "reports" / f"{workspace_id}_evaluation_report.md"
    text = report_path.read_text(encoding="utf-8")
    assert generated["report_status"] == "DRAFT_FOR_COMMITTEE_REVIEW"
    assert "DRAFT FOR HUMAN PROCUREMENT COMMITTEE REVIEW" in text
    assert "Final award decision: NULL" in text
    assert "Alpha Technologies Ltd" in text
    assert "Beta Systems Ltd" in text
    assert "page 1" not in text.lower() or "p.1" in text
