"""Actual MCP client/server tests for uploaded PDF evidence tools."""

import base64
from pathlib import Path

import pytest

from app.agent.mcp_client import call_procurement_tool
from app.services.document_store import add_pdf_document, create_workspace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCUMENTS = PROJECT_ROOT / "demo_documents"


@pytest.mark.asyncio
async def test_mcp_can_create_workspace_and_ingest_pdf_without_filesystem_access(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("TENDERGUARD_DOCUMENT_STORAGE", str(tmp_path / "documents"))
    workspace = await call_procurement_tool(
        "create_document_evaluation_workspace", {"title": "MCP ingestion test"}
    )
    pdf = (DEMO_DOCUMENTS / "tender_requirements_synthetic.pdf").read_bytes()
    uploaded = await call_procurement_tool(
        "ingest_pdf_document",
        {
            "workspace_id": workspace["workspace_id"],
            "filename": "tender_requirements_synthetic.pdf",
            "document_type": "TENDER_REQUIREMENTS",
            "pdf_base64": base64.b64encode(pdf).decode("ascii"),
        },
    )
    assert uploaded["documents"][0]["page_count"] == 1
    assert uploaded["documents"][0]["extraction_status"] == "TEXT_EXTRACTED"
    assert "source" not in uploaded["documents"][0]


@pytest.mark.asyncio
async def test_mcp_evaluates_uploaded_workspace_over_stdio(monkeypatch, tmp_path):
    monkeypatch.setenv("TENDERGUARD_DOCUMENT_STORAGE", str(tmp_path / "documents"))
    workspace_id = create_workspace("MCP document test")["workspace_id"]
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

    loaded = await call_procurement_tool(
        "load_document_workspace", {"workspace_id": workspace_id}
    )
    assert len(loaded["documents"]) == 3

    evaluated = await call_procurement_tool(
        "evaluate_document_workspace", {"workspace_id": workspace_id}
    )
    assert len(evaluated["suppliers"]) == 2
    assert evaluated["suppliers"][1]["missing_documents"] == ["REQ-TAX-CLEARANCE"]
    assert evaluated["comparison"]["historical_price_comparison_performed"] is False
