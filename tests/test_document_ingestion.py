"""PDF ingestion and deterministic page-cited evaluation tests."""

from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.services.document_store import (
    DocumentStoreError,
    add_pdf_document,
    create_workspace,
    load_workspace,
)
from mcp_servers.procurement.tools.document_evaluation import evaluate_document_workspace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCUMENTS = PROJECT_ROOT / "demo_documents"


@pytest.fixture
def document_storage(monkeypatch, tmp_path):
    storage = tmp_path / "document-storage"
    monkeypatch.setenv("TENDERGUARD_DOCUMENT_STORAGE", str(storage))
    return storage


def _upload_demo(workspace_id: str, filename: str, document_type: str):
    return add_pdf_document(
        workspace_id,
        filename=filename,
        content_type="application/pdf",
        document_type=document_type,
        content=(DEMO_DOCUMENTS / filename).read_bytes(),
    )


def test_searchable_pdf_upload_extracts_page_text_and_metadata(document_storage):
    workspace = create_workspace("Synthetic PDF test")
    uploaded = _upload_demo(
        workspace["workspace_id"],
        "tender_requirements_synthetic.pdf",
        "TENDER_REQUIREMENTS",
    )
    document = uploaded["documents"][0]
    assert document["page_count"] == 1
    assert document["extraction_status"] == "TEXT_EXTRACTED"
    assert len(document["sha256"]) == 64
    assert "Procurement Title: Supply and Installation" in document["extracted_preview"]
    assert not document_storage.joinpath(workspace["workspace_id"], "source").samefile(
        PROJECT_ROOT
    )


def test_upload_rejects_non_pdf_and_empty_text_pdf(document_storage, tmp_path):
    workspace_id = create_workspace()["workspace_id"]
    with pytest.raises(DocumentStoreError, match="PDF signature"):
        add_pdf_document(
            workspace_id,
            filename="not-really.pdf",
            content_type="application/pdf",
            document_type="TENDER_REQUIREMENTS",
            content=b"not a pdf",
        )

    blank_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with blank_path.open("wb") as file:
        writer.write(file)
    with pytest.raises(DocumentStoreError, match="No searchable text"):
        add_pdf_document(
            workspace_id,
            filename="blank.pdf",
            content_type="application/pdf",
            document_type="TENDER_REQUIREMENTS",
            content=blank_path.read_bytes(),
        )


def test_workspace_requires_one_tender_and_two_bids(document_storage):
    workspace_id = create_workspace()["workspace_id"]
    _upload_demo(
        workspace_id,
        "tender_requirements_synthetic.pdf",
        "TENDER_REQUIREMENTS",
    )
    with pytest.raises(DocumentStoreError, match="already has"):
        _upload_demo(
            workspace_id,
            "tender_requirements_synthetic.pdf",
            "TENDER_REQUIREMENTS",
        )
    assert load_workspace(workspace_id)["status"] == "DOCUMENTS_PENDING"
    _upload_demo(workspace_id, "alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID")
    ready = _upload_demo(workspace_id, "beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID")
    assert ready["status"] == "READY_FOR_EVALUATION"


def test_pdf_evaluation_is_page_cited_and_never_selects_a_supplier(document_storage):
    workspace_id = create_workspace()["workspace_id"]
    _upload_demo(
        workspace_id,
        "tender_requirements_synthetic.pdf",
        "TENDER_REQUIREMENTS",
    )
    _upload_demo(workspace_id, "alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID")
    _upload_demo(workspace_id, "beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID")

    result = evaluate_document_workspace(workspace_id)
    assert result["tender"]["title"]["value"] == "Supply and Installation of ICT Equipment"
    assert result["comparison"]["historical_price_comparison_performed"] is False
    assert [item["amount"] for item in result["comparison"]["price_order"]] == [
        42_000_000,
        47_000_000,
    ]
    alpha, beta = result["suppliers"]
    assert alpha["evidence_status"] == "COMPLIANT_WITH_AVAILABLE_EVIDENCE"
    assert beta["evidence_status"] == "VERIFIED_NONCOMPLIANT"
    assert "REQ-TAX-CLEARANCE" in beta["missing_documents"]
    assert beta["deadline_check"]["status"] == "VERIFIED_NONCOMPLIANT"
    assert beta["risk_flags"][0]["code"] == "ENTITY_NAME_INCONSISTENCY"
    assert all(
        source["page"] >= 1
        for supplier in result["suppliers"]
        for finding in supplier["document_checks"]
        for source in finding["sources"]
    )
    assert "winner" not in str(result).lower()
    assert "award decision" not in str(result).lower()
