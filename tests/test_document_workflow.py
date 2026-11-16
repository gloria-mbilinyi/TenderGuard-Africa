"""LangGraph orchestration test for uploaded PDF evaluation."""

from pathlib import Path

import pytest

from app.agent import document_workflow
from app.agent.ollama_client import EvaluationPlan, EvidenceSummary
from app.services.document_store import add_pdf_document, create_workspace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCUMENTS = PROJECT_ROOT / "demo_documents"


@pytest.mark.asyncio
async def test_document_langgraph_calls_mcp_and_stops_for_human_review(monkeypatch, tmp_path):
    monkeypatch.setenv("TENDERGUARD_DOCUMENT_STORAGE", str(tmp_path / "documents"))
    workspace_id = create_workspace("LangGraph PDF test")["workspace_id"]
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

    async def fake_plan(requested_workspace_id):
        assert requested_workspace_id == workspace_id
        return EvaluationPlan(
            tool_sequence=["load_document_workspace", "evaluate_document_workspace"],
            rationale="Load validated PDFs before evaluating page-cited evidence.",
        )

    async def fake_synthesis(evidence):
        assert evidence["suppliers"][1]["missing_documents"] == ["REQ-TAX-CLEARANCE"]
        return EvidenceSummary(
            review_priority="ATTENTION_REQUIRED",
            summary="Evidence prepared for committee review.",
            reasons=["Page-cited missing evidence requires attention."],
            human_committee_required=True,
            final_award_decision=None,
        )

    monkeypatch.setattr(document_workflow, "plan_document_evaluation", fake_plan)
    monkeypatch.setattr(document_workflow, "synthesize_document_evidence", fake_synthesis)
    result = await document_workflow.document_procurement_agent.ainvoke(
        {"workspace_id": workspace_id, "status": "STARTED"}
    )
    assert result["status"] == "AWAITING_HUMAN_REVIEW"
    assert result["completed_tools"] == [
        "load_document_workspace",
        "evaluate_document_workspace",
    ]
    assert result["decision_support"]["human_committee_required"] is True
    assert result["decision_support"]["final_award_decision"] is None
    assert len(result["document_evaluation"]["suppliers"]) == 2
