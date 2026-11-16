import re
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = (PROJECT_ROOT / "reports").resolve()
REPORT_NAME_PATTERN = re.compile(r"^(?P<bid_id>[A-Za-z0-9_-]+)_evaluation_report\.md$")
REQUIRED_REPORT_MARKER = "DRAFT FOR HUMAN PROCUREMENT COMMITTEE REVIEW"


def _is_generated_draft(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as report:
            return REQUIRED_REPORT_MARKER in report.read(4096)
    except (OSError, UnicodeDecodeError):
        return False


def list_generated_reports() -> list[dict[str, object]]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for path in sorted(REPORTS_DIR.glob("*_evaluation_report.md"), reverse=True):
        match = REPORT_NAME_PATTERN.fullmatch(path.name)
        if match is None or not _is_generated_draft(path):
            continue
        details = path.stat()
        reports.append(
            {
                "filename": path.name,
                "bid_id": match.group("bid_id"),
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
    if requested.parent != REPORTS_DIR or not requested.is_file() or not _is_generated_draft(requested):
        raise FileNotFoundError("Report was not found.")
    return requested
