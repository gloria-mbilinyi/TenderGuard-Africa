import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from app.api.models import DocumentEvaluationResponse
from app.services.document_store import (
    WORKSPACE_ID_PATTERN,
    DocumentStoreError,
    load_evaluation_result,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = (PROJECT_ROOT / "reports").resolve()
REPORT_NAME_PATTERN = re.compile(r"^(?P<bid_id>[A-Za-z0-9_-]+)_evaluation_report\.md$")
REQUIRED_REPORT_MARKER = "DRAFT FOR HUMAN PROCUREMENT COMMITTEE REVIEW"
METADATA_READ_LIMIT = 16 * 1024


def _is_generated_draft(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as report:
            return REQUIRED_REPORT_MARKER in report.read(4096)
    except (OSError, UnicodeDecodeError):
        return False


def _section_fields(text: str, heading: str) -> dict[str, str]:
    """Read only a generated template section, never arbitrary report findings."""
    sections = re.split(r"(?m)^## ", text)
    for section in reversed(sections[1:]):
        title, _, body = section.partition("\n")
        if title.strip().casefold() == heading.casefold():
            fields = {}
            for line in body.splitlines():
                key, separator, value = line.removeprefix("- ").partition(": ")
                if separator:
                    fields[key.strip().casefold()] = value.strip()
            return fields
    return {}


def _display_text(value: object, limit: int = 300) -> str | None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return None
    return " ".join(value.split())


def _generation_metadata(fields: dict[str, str]) -> dict[str, str | None]:
    generated_at = None
    try:
        parsed = datetime.fromisoformat(fields.get("generated at", ""))
        if parsed.utcoffset() is not None:
            generated_at = parsed.astimezone(UTC).isoformat()
    except ValueError:
        pass
    return {
        "generated_at": generated_at,
        "approved_by": _display_text(
            fields.get("draft report generation approved by")
            or fields.get("report generation approved by"),
            limit=200,
        ),
    }


def _report_metadata(path: Path, reference: str) -> dict[str, object]:
    # Read bounded header/footer sections; do not return report text, evidence, or paths.
    with path.open("rb") as report:
        header = report.read(METADATA_READ_LIMIT).decode("utf-8", errors="replace")
        report.seek(max(0, path.stat().st_size - METADATA_READ_LIMIT))
        footer = report.read(METADATA_READ_LIMIT).decode("utf-8", errors="replace")
    authorization = _section_fields(footer, "Human authorization") or _section_fields(
        footer, "Human-in-the-Loop Handoff"
    )
    metadata: dict[str, object] = _generation_metadata(authorization)
    if not WORKSPACE_ID_PATTERN.fullmatch(reference):
        return metadata

    metadata["workspace_id"] = reference
    report_evaluation = _section_fields(header, "Evaluation")
    if report_evaluation.get("workspace") != reference:
        return metadata
    try:
        evaluation = DocumentEvaluationResponse.model_validate(load_evaluation_result(reference))
    except (DocumentStoreError, OSError, UnicodeError, ValidationError):
        return metadata
    if evaluation.workspace_id != reference or evaluation.evaluation_id != report_evaluation.get(
        "evaluation id"
    ):
        return metadata

    title = evaluation.tender.title
    metadata["tender_title"] = _display_text(title.value) if title.status == "VERIFIED" else None
    names = [
        _display_text(supplier.supplier_name.value)
        for supplier in evaluation.suppliers
        if supplier.supplier_name.status == "VERIFIED"
    ]
    metadata["supplier_names"] = list(dict.fromkeys(name for name in names if name))
    return metadata


def list_generated_reports() -> list[dict[str, object]]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for path in sorted(REPORTS_DIR.glob("*_evaluation_report.md"), reverse=True):
        match = REPORT_NAME_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        try:
            # Apply the same directory/filename/draft checks as the download route.
            safe_path = resolve_generated_report(path.name)
            details = safe_path.stat()
            metadata = _report_metadata(safe_path, match.group("bid_id"))
        except (FileNotFoundError, OSError):
            continue
        reports.append(
            {
                "filename": path.name,
                "bid_id": match.group("bid_id"),
                **metadata,
                "status": "DRAFT_FOR_COMMITTEE_REVIEW",
                "size_bytes": details.st_size,
                "modified_at": datetime.fromtimestamp(details.st_mtime, UTC).isoformat(),
                "download_url": f"/api/browser/reports/{path.name}/download",
            }
        )
    return reports


def resolve_generated_report(filename: str) -> Path:
    if REPORT_NAME_PATTERN.fullmatch(filename) is None:
        raise FileNotFoundError("Report was not found.")
    requested = (REPORTS_DIR / filename).resolve()
    if (
        requested.parent != REPORTS_DIR
        or not requested.is_file()
        or not _is_generated_draft(requested)
    ):
        raise FileNotFoundError("Report was not found.")
    return requested
