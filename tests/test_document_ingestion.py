"""PDF ingestion and deterministic page-cited evaluation tests."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from app.agent import ollama_client
from app.services.document_store import (
    DocumentStoreError,
    add_pdf_document,
    create_workspace,
    load_workspace,
)
from mcp_servers.procurement.tools import document_evaluation
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
    assert not document_storage.joinpath(workspace["workspace_id"], "source").samefile(PROJECT_ROOT)


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
    assert all("deadline_check" not in supplier for supplier in result["suppliers"])
    assert "SUBMISSION_DEADLINE" not in str(result)
    assert beta["risk_flags"][0]["code"] == "ENTITY_NAME_INCONSISTENCY"
    assert all(
        source["page"] >= 1
        for supplier in result["suppliers"]
        for finding in supplier["document_checks"]
        for source in finding["sources"]
    )
    assert "winner" not in str(result).lower()
    assert "award decision" not in str(result).lower()


@pytest.mark.parametrize(
    ("filename", "expected_date"),
    [
        ("tender_requirements_synthetic.pdf", "Submission Deadline: 2026-12-15 12:00 EAT"),
        ("alpha_supplier_bid_synthetic.pdf", "Submission Date: 2026-12-14 10:15 EAT"),
        ("beta_supplier_bid_synthetic.pdf", "Submission Date: 2026-12-14 09:30 EAT"),
    ],
)
def test_regenerated_demo_pdf_contains_expected_date(filename, expected_date):
    reader = PdfReader(DEMO_DOCUMENTS / filename)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert expected_date in text
    assert "SYNTHETIC DEMONSTRATION DATA" in text


@pytest.mark.asyncio
async def test_pdf_submission_metadata_cannot_change_findings_or_priority(
    document_storage, monkeypatch
):
    workspace_id = create_workspace()["workspace_id"]
    for filename, document_type in [
        ("tender_requirements_synthetic.pdf", "TENDER_REQUIREMENTS"),
        ("alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
        ("beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
    ]:
        _upload_demo(workspace_id, filename, document_type)
    baseline = evaluate_document_workspace(workspace_id)
    original_pages = document_evaluation._pages
    prompts = []

    async def fake_chat_structured(**kwargs):
        prompts.append(kwargs["user_prompt"])
        assert "submitted_at" not in kwargs["user_prompt"]
        assert "submission_deadline" not in kwargs["user_prompt"]
        return json.dumps(
            {"review_priority": "STANDARD_REVIEW", "summary": "Evidence reviewed.", "reasons": []}
        )

    monkeypatch.setattr(ollama_client, "_chat_structured", fake_chat_structured)
    baseline_summary = await ollama_client.synthesize_document_evidence(baseline)
    for timestamp in ["2026-12-01 09:30 EAT", "2027-01-01 09:30 EAT", "invalid", None]:

        def changed_pages(requested_workspace, document, timestamp=timestamp):
            pages = deepcopy(original_pages(requested_workspace, document))
            for page in pages:
                for label in ["Submission Date", "Submission Deadline"]:
                    replacement = f"{label}: {timestamp}\n" if timestamp else ""
                    page["text"] = re.sub(rf"(?m)^{label}:.*\n?", replacement, page["text"])
            return pages

        monkeypatch.setattr(document_evaluation, "_pages", changed_pages)
        evidence = evaluate_document_workspace(workspace_id)
        assert evidence["comparison"] == baseline["comparison"]
        for actual, expected in zip(evidence["suppliers"], baseline["suppliers"], strict=True):
            assert "deadline_check" not in actual
            assert {k: v for k, v in actual.items() if k != "submitted_at"} == {
                k: v for k, v in expected.items() if k != "submitted_at"
            }
        summary = await ollama_client.synthesize_document_evidence(evidence)
        assert summary == baseline_summary
        assert summary.review_priority == "ATTENTION_REQUIRED"
        assert summary.human_committee_required is True
        assert summary.final_award_decision is None
    assert all(prompt == prompts[0] for prompt in prompts)
