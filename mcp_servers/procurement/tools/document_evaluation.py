"""Deterministic, page-cited evaluation of uploaded procurement PDFs."""

import re
from datetime import datetime
from typing import Any

from app.services.document_store import load_document_pages, load_workspace

SECTION_HEADINGS = {
    "MANDATORY REQUIRED DOCUMENTS",
    "MANDATORY ELIGIBILITY CRITERIA",
    "TECHNICAL SPECIFICATIONS",
    "FINANCIAL REQUIREMENTS",
    "EVALUATION CRITERIA",
    "SUBMITTED DOCUMENTS",
    "ELIGIBILITY EVIDENCE",
    "TECHNICAL RESPONSE",
    "FINANCIAL OFFER",
    "SUPPLIER DECLARATIONS",
}
ITEM_PATTERN = re.compile(r"^-\s*([A-Z][A-Z0-9_-]{1,40})\s*\|\s*(.+)$")


def _citation(document: dict[str, Any], page: int, quote: str) -> dict[str, Any]:
    return {
        "document_id": document["document_id"],
        "filename": document["filename"],
        "page": page,
        "quote": quote[:500],
    }


def _pages(workspace_id: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    return load_document_pages(workspace_id, document["document_id"])["pages"]


def _field(
    document: dict[str, Any],
    pages: list[dict[str, Any]],
    labels: list[str],
) -> dict[str, Any]:
    matches = []
    lowered = [f"{label.lower()}:" for label in labels]
    for page in pages:
        for line in page["text"].splitlines():
            normalized = line.strip()
            for prefix in lowered:
                if normalized.lower().startswith(prefix):
                    value = normalized[len(prefix) :].strip()
                    if value:
                        matches.append((value, _citation(document, page["page"], normalized)))
                    break
    if not matches:
        return {"value": None, "status": "NOT_FOUND", "sources": []}
    unique_values = {value.casefold() for value, _ in matches}
    return {
        "value": matches[0][0],
        "status": "VERIFIED" if len(unique_values) == 1 else "AMBIGUOUS",
        "sources": [source for _, source in matches[:3]],
    }


def _section_items(
    document: dict[str, Any],
    pages: list[dict[str, Any]],
    heading: str,
) -> list[dict[str, Any]]:
    items = []
    active = False
    for page in pages:
        for line in page["text"].splitlines():
            normalized = line.strip()
            upper = normalized.upper()
            if upper == heading:
                active = True
                continue
            if active and upper in SECTION_HEADINGS:
                active = False
                continue
            if not active:
                continue
            match = ITEM_PATTERN.fullmatch(normalized)
            if match:
                items.append(
                    {
                        "code": match.group(1),
                        "label": match.group(2).strip(),
                        "source": _citation(document, page["page"], normalized),
                    }
                )
    return items


def _parse_price(field: dict[str, Any]) -> tuple[float | None, str | None]:
    value = field.get("value")
    if not isinstance(value, str):
        return None, None
    match = re.search(r"\b([A-Z]{3})\s+([0-9][0-9,]*(?:\.[0-9]+)?)\b", value.upper())
    if not match:
        return None, None
    return float(match.group(2).replace(",", "")), match.group(1)


def _date_value(field: dict[str, Any]) -> datetime | None:
    value = field.get("value")
    if not isinstance(value, str):
        return None
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2}))?", value)
    if not match:
        return None
    try:
        return datetime.fromisoformat(
            f"{match.group(1)}T{match.group(2) or '00'}:{match.group(3) or '00'}:00"
        )
    except ValueError:
        return None


def extract_tender(workspace_id: str, document: dict[str, Any]) -> dict[str, Any]:
    pages = _pages(workspace_id, document)
    return {
        "document_id": document["document_id"],
        "filename": document["filename"],
        "tender_id": _field(document, pages, ["Tender ID", "Procurement Reference"]),
        "title": _field(document, pages, ["Procurement Title", "Tender Title"]),
        "procuring_entity": _field(document, pages, ["Procuring Entity", "Buyer"]),
        "submission_deadline": _field(document, pages, ["Submission Deadline"]),
        "currency": _field(document, pages, ["Tender Currency", "Currency"]),
        "required_documents": _section_items(
            document, pages, "MANDATORY REQUIRED DOCUMENTS"
        ),
        "eligibility_criteria": _section_items(
            document, pages, "MANDATORY ELIGIBILITY CRITERIA"
        ),
        "technical_specifications": _section_items(
            document, pages, "TECHNICAL SPECIFICATIONS"
        ),
        "financial_requirements": _section_items(
            document, pages, "FINANCIAL REQUIREMENTS"
        ),
        "evaluation_criteria": _section_items(document, pages, "EVALUATION CRITERIA"),
    }


def _check_requirements(
    requirements: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    *,
    category: str,
) -> list[dict[str, Any]]:
    evidence_by_code = {item["code"]: item for item in evidence}
    findings = []
    for requirement in requirements:
        supplied = evidence_by_code.get(requirement["code"])
        sources = [requirement["source"]]
        if supplied is None:
            findings.append(
                {
                    "code": requirement["code"],
                    "requirement": requirement["label"],
                    "status": "MISSING_EVIDENCE",
                    "finding": (
                        f"No page-cited {category} evidence was found for "
                        f"{requirement['code']}."
                    ),
                    "sources": sources,
                }
            )
            continue
        sources.append(supplied["source"])
        text = supplied["label"].upper()
        if any(token in text for token in ["NOT MET", "DOES NOT COMPLY", "NONCOMPLIANT"]):
            status = "VERIFIED_NONCOMPLIANT"
            finding = f"The supplier document explicitly records {requirement['code']} as not met."
        elif any(token in text for token in ["PARTIAL", "UNCERTAIN", "REQUIRES REVIEW"]):
            status = "REQUIRES_HUMAN_REVIEW"
            finding = f"The evidence for {requirement['code']} is partial or requires human review."
        else:
            status = "VERIFIED_COMPLIANT"
            finding = f"The supplier PDF contains page-cited evidence for {requirement['code']}."
        findings.append(
            {
                "code": requirement["code"],
                "requirement": requirement["label"],
                "status": status,
                "finding": finding,
                "sources": sources,
            }
        )
    return findings


def evaluate_supplier(
    workspace_id: str,
    tender: dict[str, Any],
    document: dict[str, Any],
) -> dict[str, Any]:
    pages = _pages(workspace_id, document)
    supplier_name = _field(document, pages, ["Supplier Name", "Bidder Name"])
    supplier_identifier = _field(
        document, pages, ["Supplier Identifier", "Registration Number"]
    )
    registered_name = _field(document, pages, ["Registered Entity Name"])
    bid_reference = _field(document, pages, ["Bid Reference", "Bid ID"])
    submitted_at = _field(document, pages, ["Submission Date", "Submitted At"])
    raw_price = _field(document, pages, ["Bid Price", "Total Bid Price"])
    price, currency = _parse_price(raw_price)
    bid_price = {
        "value": price,
        "status": "VERIFIED" if price is not None else "NOT_FOUND",
        "sources": raw_price["sources"] if price is not None else [],
    }
    currency_field = {
        "value": currency,
        "status": "VERIFIED" if currency else "NOT_FOUND",
        "sources": raw_price["sources"] if currency else [],
    }

    submitted_documents = _section_items(document, pages, "SUBMITTED DOCUMENTS")
    eligibility_evidence = _section_items(document, pages, "ELIGIBILITY EVIDENCE")
    technical_response = _section_items(document, pages, "TECHNICAL RESPONSE")
    document_checks = _check_requirements(
        tender["required_documents"], submitted_documents, category="document"
    )
    eligibility_checks = _check_requirements(
        tender["eligibility_criteria"], eligibility_evidence, category="eligibility"
    )
    technical_checks = _check_requirements(
        tender["technical_specifications"], technical_response, category="technical"
    )

    deadline = _date_value(tender["submission_deadline"])
    submission = _date_value(submitted_at)
    deadline_sources = [
        *tender["submission_deadline"]["sources"],
        *submitted_at["sources"],
    ]
    if deadline is None or submission is None:
        deadline_check = {
            "code": "SUBMISSION_DEADLINE",
            "requirement": "Submission must occur by the stated deadline.",
            "status": "UNVERIFIED",
            "finding": (
                "Deadline compliance is unverified because a reliable deadline or "
                "submission timestamp was not found in the PDFs."
            ),
            "sources": deadline_sources,
        }
    elif submission <= deadline:
        deadline_check = {
            "code": "SUBMISSION_DEADLINE",
            "requirement": "Submission must occur by the stated deadline.",
            "status": "VERIFIED_COMPLIANT",
            "finding": "The PDF submission date is on or before the tender deadline.",
            "sources": deadline_sources,
        }
    else:
        deadline_check = {
            "code": "SUBMISSION_DEADLINE",
            "requirement": "Submission must occur by the stated deadline.",
            "status": "VERIFIED_NONCOMPLIANT",
            "finding": "The PDF submission date is after the stated tender deadline.",
            "sources": deadline_sources,
        }

    if price is None:
        financial_check = {
            "code": "BID_PRICE",
            "requirement": "A bid price and currency must be evidenced.",
            "status": "MISSING_EVIDENCE",
            "finding": "No reliable bid price and currency were extracted from the PDF.",
            "sources": [],
        }
    else:
        financial_check = {
            "code": "BID_PRICE",
            "requirement": "A bid price and currency must be evidenced.",
            "status": "VERIFIED_COMPLIANT",
            "finding": f"The PDF records a bid price of {currency} {price:,.2f}.",
            "sources": raw_price["sources"],
        }

    risk_flags = []
    if (
        supplier_name["status"] == "VERIFIED"
        and registered_name["status"] == "VERIFIED"
        and str(supplier_name["value"]).casefold() != str(registered_name["value"]).casefold()
    ):
        risk_flags.append(
            {
                "code": "ENTITY_NAME_INCONSISTENCY",
                "severity": "MEDIUM",
                "finding": (
                    "The supplier name and registered entity name differ within the "
                    "submitted PDF. This is a data-consistency flag for human review, "
                    "not a finding of misconduct."
                ),
                "sources": [*supplier_name["sources"], *registered_name["sources"]],
            }
        )

    all_findings = [
        *document_checks,
        *eligibility_checks,
        *technical_checks,
        deadline_check,
        financial_check,
    ]
    statuses = {item["status"] for item in all_findings}
    if "VERIFIED_NONCOMPLIANT" in statuses:
        evidence_status = "VERIFIED_NONCOMPLIANT"
    elif statuses & {"MISSING_EVIDENCE", "REQUIRES_HUMAN_REVIEW", "UNVERIFIED"}:
        evidence_status = "EVIDENCE_INCOMPLETE"
    else:
        evidence_status = "COMPLIANT_WITH_AVAILABLE_EVIDENCE"

    return {
        "document_id": document["document_id"],
        "filename": document["filename"],
        "supplier_name": supplier_name,
        "supplier_identifier": supplier_identifier,
        "bid_reference": bid_reference,
        "submitted_at": submitted_at,
        "bid_price": bid_price,
        "currency": currency_field,
        "document_checks": document_checks,
        "eligibility_checks": eligibility_checks,
        "technical_checks": technical_checks,
        "deadline_check": deadline_check,
        "financial_check": financial_check,
        "missing_documents": [
            item["code"] for item in document_checks if item["status"] == "MISSING_EVIDENCE"
        ],
        "risk_flags": risk_flags,
        "evidence_status": evidence_status,
    }


def evaluate_document_workspace(workspace_id: str) -> dict[str, Any]:
    workspace = load_workspace(workspace_id, include_previews=False)
    tender_documents = [
        item for item in workspace["documents"] if item["document_type"] == "TENDER_REQUIREMENTS"
    ]
    bid_documents = [
        item for item in workspace["documents"] if item["document_type"] == "SUPPLIER_BID"
    ]
    if len(tender_documents) != 1 or len(bid_documents) < 2:
        raise ValueError(
            "A document evaluation requires exactly one tender PDF and at least two bid PDFs."
        )

    tender = extract_tender(workspace_id, tender_documents[0])
    suppliers = [evaluate_supplier(workspace_id, tender, item) for item in bid_documents]
    currencies = {
        item["currency"]["value"]
        for item in suppliers
        if item["currency"]["status"] == "VERIFIED"
    }
    priced = [
        item
        for item in suppliers
        if item["bid_price"]["status"] == "VERIFIED"
        and item["currency"]["status"] == "VERIFIED"
    ]
    directly_comparable = len(priced) == len(suppliers) and len(currencies) == 1
    price_order = []
    if directly_comparable:
        for item in sorted(priced, key=lambda value: float(value["bid_price"]["value"])):
            price_order.append(
                {
                    "document_id": item["document_id"],
                    "supplier_name": str(item["supplier_name"]["value"] or "Unknown supplier"),
                    "amount": item["bid_price"]["value"],
                    "currency": item["currency"]["value"],
                    "source": item["bid_price"]["sources"][0],
                }
            )

    notes = [
        (
            "Price order is a direct comparison of submitted bids only; it is not a ranking, "
            "recommendation, award, or value-for-money conclusion."
        ),
        (
            "No historical price comparison was performed because the uploaded-document "
            "workflow has not established a suitable comparable historical dataset."
        ),
    ]
    if not directly_comparable:
        notes.insert(
            0,
            "Submitted prices could not all be directly compared because a price, currency, "
            "or common currency was not verified for every supplier.",
        )
    return {
        "workspace_id": workspace_id,
        "tender": tender,
        "suppliers": suppliers,
        "comparison": {
            "supplier_count": len(suppliers),
            "directly_comparable_prices": directly_comparable,
            "price_order": price_order,
            "historical_price_comparison_performed": False,
            "notes": notes,
        },
    }


def load_document_workspace_evidence(workspace_id: str) -> dict[str, Any]:
    workspace = load_workspace(workspace_id, include_previews=False)
    return {
        "workspace_id": workspace["workspace_id"],
        "title": workspace["title"],
        "status": workspace["status"],
        "documents": [
            {
                "document_id": item["document_id"],
                "document_type": item["document_type"],
                "filename": item["filename"],
                "page_count": item["page_count"],
                "extraction_status": item["extraction_status"],
            }
            for item in workspace["documents"]
        ],
    }
