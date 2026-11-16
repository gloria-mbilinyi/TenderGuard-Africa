"""Generate an authorized draft report for an uploaded-document evaluation."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.document_store import load_evaluation_result

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports"


def _report_path_for_output(report_path: Path) -> str:
    try:
        return report_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(report_path)


def _source_text(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "No page citation available"
    return "; ".join(
        f"{source['filename']} p.{source['page']}: {source['quote']}" for source in sources
    )


def generate_document_evaluation_report_file(
    workspace_id: str,
    approved_by: str,
) -> dict[str, Any]:
    approved_by = approved_by.strip()
    if not approved_by:
        raise PermissionError(
            "Named human approval is required before generating the draft report."
        )
    result = load_evaluation_result(workspace_id)
    if (
        result.get("status") != "AWAITING_HUMAN_REVIEW"
        or result.get("final_award_decision") is not None
    ):
        raise ValueError("The document evaluation has not reached the required review state.")

    supplier_sections = []
    for supplier in result["suppliers"]:
        checks = [
            *supplier["document_checks"],
            *supplier["eligibility_checks"],
            *supplier["technical_checks"],
            supplier["deadline_check"],
            supplier["financial_check"],
        ]
        check_lines = [
            f"- **{item['code']} — {item['status']}**: {item['finding']} "
            f"(Evidence: {_source_text(item['sources'])})"
            for item in checks
        ]
        flag_lines = [
            f"- **{flag['code']} — {flag['severity']}**: {flag['finding']} "
            f"(Evidence: {_source_text(flag['sources'])})"
            for flag in supplier["risk_flags"]
        ] or ["- No supplier-data consistency flags were identified in the uploaded PDF."]
        supplier_sections.append(
            f"""### {supplier['supplier_name']['value'] or supplier['filename']}

- Evidence status: {supplier['evidence_status']}
- Bid price: {supplier['currency']['value'] or 'UNVERIFIED'} {supplier['bid_price']['value'] or 'UNVERIFIED'}
- Missing mandatory document evidence: {', '.join(supplier['missing_documents']) or 'None identified'}

#### Findings

{chr(10).join(check_lines)}

#### Supplier-data review flags

{chr(10).join(flag_lines)}
"""
        )

    price_lines = [
        f"- {item['supplier_name']}: {item['currency']} {item['amount']:,.2f} "
        f"(Evidence: {_source_text([item['source']])})"
        for item in result["comparison"]["price_order"]
    ] or ["- Direct price ordering was not available from verified common-currency evidence."]
    generated_at = datetime.now(UTC).isoformat()
    report = f"""# TenderGuard Africa Uploaded-Document Evaluation Report

## Review status

DRAFT FOR HUMAN PROCUREMENT COMMITTEE REVIEW

This report is decision support only. It does not award, reject, disqualify, rank,
or select a supplier. The authorised procurement committee retains the final decision.

## Evaluation

- Workspace: {workspace_id}
- Evaluation ID: {result['evaluation_id']}
- Review priority: {result['decision_support']['review_priority']}
- Final award decision: NULL

## Tender evidence

- Title: {result['tender']['title']['value'] or 'UNVERIFIED'}
- Procuring entity: {result['tender']['procuring_entity']['value'] or 'UNVERIFIED'}
- Submission deadline: {result['tender']['submission_deadline']['value'] or 'UNVERIFIED'}
- Source: {_source_text(result['tender']['title']['sources'])}

## Supplier evaluations

{chr(10).join(supplier_sections)}

## Direct submitted-price comparison

{chr(10).join(price_lines)}

{chr(10).join(f'- {note}' for note in result['comparison']['notes'])}

## AI-assisted decision support

{result['decision_support']['summary']}

{chr(10).join(f'- {reason}' for reason in result['decision_support']['reasons'])}

## Human authorization

- Draft report generation approved by: {approved_by}
- Generated at: {generated_at}
- Human procurement committee review required: TRUE
- Final award decision: NULL
"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{workspace_id}_evaluation_report.md"
    report_path.write_text(report, encoding="utf-8")
    return {
        "workspace_id": workspace_id,
        "report_path": _report_path_for_output(report_path),
        "report_status": "DRAFT_FOR_COMMITTEE_REVIEW",
        "approved_by": approved_by,
        "generated_at": generated_at,
        "final_decision_made": False,
    }
