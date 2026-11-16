"""Safe storage and text extraction for uploaded procurement PDFs."""

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from pypdf import PdfReader
from pypdf.errors import PdfReadError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "storage" / "document_evaluations"
WORKSPACE_ID_PATTERN = re.compile(r"^EVL-[A-F0-9]{16}$")
DOCUMENT_ID_PATTERN = re.compile(r"^DOC-[A-F0-9]{16}$")
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")
DocumentType = Literal["TENDER_REQUIREMENTS", "SUPPLIER_BID"]
_store_lock = Lock()


class DocumentStoreError(ValueError):
    """Raised when an uploaded workspace or document cannot be accepted."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def storage_root() -> Path:
    configured = os.getenv("TENDERGUARD_DOCUMENT_STORAGE", "").strip()
    root = Path(configured).expanduser() if configured else DEFAULT_STORAGE_ROOT
    return root.resolve()


def _max_file_bytes() -> int:
    configured = int(os.getenv("TENDERGUARD_MAX_PDF_MB", "10"))
    return max(1, min(configured, 25)) * 1024 * 1024


def max_pdf_bytes() -> int:
    return _max_file_bytes()


def _max_pages() -> int:
    configured = int(os.getenv("TENDERGUARD_MAX_PDF_PAGES", "80"))
    return max(1, min(configured, 200))


def _workspace_dir(workspace_id: str) -> Path:
    if not WORKSPACE_ID_PATTERN.fullmatch(workspace_id):
        raise DocumentStoreError("Invalid document-evaluation workspace identifier.")
    root = storage_root()
    candidate = (root / workspace_id).resolve()
    if candidate.parent != root:
        raise DocumentStoreError("Workspace path escaped the configured storage boundary.")
    return candidate


def _document_id(value: str) -> str:
    if not DOCUMENT_ID_PATTERN.fullmatch(value):
        raise DocumentStoreError("Invalid uploaded-document identifier.")
    return value


def _manifest_path(workspace_id: str) -> Path:
    return _workspace_dir(workspace_id) / "manifest.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise DocumentStoreError("Stored document metadata is unavailable or invalid.") from exc
    if not isinstance(value, dict):
        raise DocumentStoreError("Stored document metadata is invalid.")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def _sanitize_filename(filename: str) -> str:
    basename = Path(filename.replace("\\", "/")).name.strip()
    cleaned = SAFE_FILENAME_PATTERN.sub("_", basename)[:120].strip(" .")
    if not cleaned or Path(cleaned).suffix.lower() != ".pdf":
        raise DocumentStoreError("Only files with a .pdf extension are accepted.")
    return cleaned


def _normalize_text(value: str) -> str:
    lines = [" ".join(line.replace("\x00", " ").split()) for line in value.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _reject_active_content(reader: PdfReader) -> None:
    root = reader.trailer.get("/Root")
    if root is None:
        return
    prohibited = {"/OpenAction", "/AA"}
    if any(root.get(name) is not None for name in prohibited):
        raise DocumentStoreError("PDFs containing automatic actions are not accepted.")
    names = root.get("/Names")
    if names is not None and any(
        names.get(name) is not None for name in ("/JavaScript", "/EmbeddedFiles")
    ):
        raise DocumentStoreError("PDFs containing scripts or embedded files are not accepted.")
    for page in reader.pages:
        if page.get("/AA") is not None:
            raise DocumentStoreError("PDFs containing page actions are not accepted.")


def _extract_pdf(content: bytes) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    from io import BytesIO

    try:
        reader = PdfReader(BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise DocumentStoreError("Encrypted PDFs are not accepted for evaluation.")
        if not reader.pages:
            raise DocumentStoreError("The PDF contains no pages.")
        if len(reader.pages) > _max_pages():
            raise DocumentStoreError(
                f"The PDF exceeds the {_max_pages()}-page limit for this deployment."
            )
        _reject_active_content(reader)
        pages = []
        for number, page in enumerate(reader.pages, start=1):
            text = _normalize_text(page.extract_text() or "")
            pages.append({"page": number, "text": text[:100_000]})
        metadata = reader.metadata or {}
    except DocumentStoreError:
        raise
    except (PdfReadError, OSError, ValueError, TypeError, KeyError) as exc:
        raise DocumentStoreError("The uploaded file is not a readable PDF.") from exc

    if not any(page["text"] for page in pages):
        raise DocumentStoreError(
            "No searchable text was extracted. Image-only PDFs require OCR, which is "
            "not enabled in this demonstration build."
        )
    return pages, {
        "title": str(metadata.get("/Title"))[:200] if metadata.get("/Title") else None,
        "author": str(metadata.get("/Author"))[:200] if metadata.get("/Author") else None,
    }


def _status_for_documents(documents: list[dict[str, Any]]) -> str:
    tender_count = sum(item["document_type"] == "TENDER_REQUIREMENTS" for item in documents)
    bid_count = sum(item["document_type"] == "SUPPLIER_BID" for item in documents)
    return "READY_FOR_EVALUATION" if tender_count == 1 and bid_count >= 2 else "DOCUMENTS_PENDING"


def create_workspace(title: str | None = None) -> dict[str, Any]:
    workspace_id = f"EVL-{uuid4().hex[:16].upper()}"
    workspace_dir = _workspace_dir(workspace_id)
    created_at = _now()
    manifest = {
        "workspace_id": workspace_id,
        "title": (title or "Uploaded procurement evaluation").strip()[:200],
        "created_at": created_at,
        "updated_at": created_at,
        "status": "DOCUMENTS_PENDING",
        "documents": [],
        "latest_evaluation_id": None,
    }
    with _store_lock:
        workspace_dir.mkdir(parents=True, exist_ok=False)
        (workspace_dir / "source").mkdir()
        (workspace_dir / "extracted").mkdir()
        _write_json(_manifest_path(workspace_id), manifest)
    return manifest


def load_workspace(workspace_id: str, *, include_previews: bool = True) -> dict[str, Any]:
    manifest_path = _manifest_path(workspace_id)
    if not manifest_path.is_file():
        raise FileNotFoundError("Document-evaluation workspace was not found.")
    manifest = _read_json(manifest_path)
    if include_previews:
        for document in manifest.get("documents", []):
            extracted = load_document_pages(workspace_id, document["document_id"])
            joined = "\n\n".join(page["text"] for page in extracted["pages"])
            document["extracted_preview"] = joined[:2_500]
    return manifest


def list_workspaces() -> list[dict[str, Any]]:
    root = storage_root()
    if not root.is_dir():
        return []
    workspaces = []
    for path in sorted(root.glob("EVL-*/manifest.json"), reverse=True):
        try:
            manifest = _read_json(path)
        except DocumentStoreError:
            continue
        manifest["documents"] = [
            {key: value for key, value in item.items() if key != "extracted_preview"}
            for item in manifest.get("documents", [])
        ]
        workspaces.append(manifest)
    return workspaces


def add_pdf_document(
    workspace_id: str,
    *,
    filename: str,
    content_type: str,
    document_type: DocumentType,
    content: bytes,
    supplier_name: str | None = None,
) -> dict[str, Any]:
    if content_type.lower().split(";", 1)[0].strip() != "application/pdf":
        raise DocumentStoreError("The upload Content-Type must be application/pdf.")
    safe_filename = _sanitize_filename(filename)
    if not content or len(content) > _max_file_bytes():
        raise DocumentStoreError(
            f"PDF size must be between 1 byte and {_max_file_bytes() // (1024 * 1024)} MB."
        )
    if not content.startswith(b"%PDF-"):
        raise DocumentStoreError("The uploaded content does not have a PDF signature.")
    pages, pdf_metadata = _extract_pdf(content)
    document_id = f"DOC-{uuid4().hex[:16].upper()}"

    with _store_lock:
        manifest = load_workspace(workspace_id, include_previews=False)
        documents = manifest["documents"]
        if document_type == "TENDER_REQUIREMENTS" and any(
            item["document_type"] == "TENDER_REQUIREMENTS" for item in documents
        ):
            raise DocumentStoreError("This workspace already has a tender requirements PDF.")

        workspace_dir = _workspace_dir(workspace_id)
        (workspace_dir / "source" / f"{document_id}.pdf").write_bytes(content)
        extracted_record = {
            "document_id": document_id,
            "workspace_id": workspace_id,
            "filename": safe_filename,
            "document_type": document_type,
            "pages": pages,
        }
        _write_json(
            workspace_dir / "extracted" / f"{document_id}.json",
            extracted_record,
        )
        uploaded_at = _now()
        document = {
            "document_id": document_id,
            "document_type": document_type,
            "filename": safe_filename,
            "supplier_name": supplier_name.strip()[:200] if supplier_name else None,
            "content_type": "application/pdf",
            "size_bytes": len(content),
            "page_count": len(pages),
            "sha256": hashlib.sha256(content).hexdigest(),
            "uploaded_at": uploaded_at,
            "extraction_status": "TEXT_EXTRACTED",
            "pdf_metadata": pdf_metadata,
        }
        documents.append(document)
        manifest["updated_at"] = uploaded_at
        manifest["status"] = _status_for_documents(documents)
        _write_json(_manifest_path(workspace_id), manifest)

    return load_workspace(workspace_id)


def load_document_pages(workspace_id: str, document_id: str) -> dict[str, Any]:
    _document_id(document_id)
    path = _workspace_dir(workspace_id) / "extracted" / f"{document_id}.json"
    if not path.is_file():
        raise FileNotFoundError("Uploaded document was not found.")
    return _read_json(path)


def save_evaluation_result(workspace_id: str, result: dict[str, Any]) -> None:
    with _store_lock:
        manifest = load_workspace(workspace_id, include_previews=False)
        workspace_dir = _workspace_dir(workspace_id)
        _write_json(workspace_dir / "evaluation.json", result)
        manifest["status"] = "AWAITING_HUMAN_REVIEW"
        manifest["latest_evaluation_id"] = result["evaluation_id"]
        manifest["updated_at"] = result["completed_at"]
        _write_json(_manifest_path(workspace_id), manifest)


def load_evaluation_result(workspace_id: str) -> dict[str, Any]:
    path = _workspace_dir(workspace_id) / "evaluation.json"
    if not path.is_file():
        raise FileNotFoundError("This workspace has no completed document evaluation.")
    return _read_json(path)
