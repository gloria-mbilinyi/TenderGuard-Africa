"""Run a real TenderGuard evaluation from one tender PDF and multiple bid PDFs."""

import argparse
import asyncio
import json
from pathlib import Path

from app.agent.document_runner import execute_document_evaluation
from app.services.document_store import add_pdf_document, create_workspace


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate searchable procurement PDFs with LangGraph, MCP, and Ollama."
    )
    parser.add_argument("--tender", required=True, type=Path, help="Tender requirements PDF")
    parser.add_argument(
        "--bid",
        required=True,
        type=Path,
        action="append",
        help="Supplier bid PDF; provide at least twice",
    )
    parser.add_argument("--title", default="CLI uploaded-document evaluation")
    return parser


def _read_pdf(path: Path) -> bytes:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"PDF path is not a file: {resolved}")
    return resolved.read_bytes()


async def _run(args: argparse.Namespace) -> dict[str, object]:
    if len(args.bid) < 2:
        raise ValueError("Provide at least two --bid PDF paths.")
    workspace = create_workspace(args.title)
    workspace_id = workspace["workspace_id"]
    add_pdf_document(
        workspace_id,
        filename=args.tender.name,
        content_type="application/pdf",
        document_type="TENDER_REQUIREMENTS",
        content=_read_pdf(args.tender),
    )
    for bid_path in args.bid:
        add_pdf_document(
            workspace_id,
            filename=bid_path.name,
            content_type="application/pdf",
            document_type="SUPPLIER_BID",
            content=_read_pdf(bid_path),
        )
    return (await execute_document_evaluation(workspace_id)).model_dump(mode="json")


def main() -> None:
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
