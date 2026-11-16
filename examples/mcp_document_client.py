"""Example real MCP client for TenderGuard's uploaded-document workflow."""

import argparse
import asyncio
import base64
import json
from pathlib import Path

from app.agent.mcp_client import call_procurement_tool


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate procurement PDFs through MCP.")
    parser.add_argument("--tender", required=True, type=Path)
    parser.add_argument("--bid", required=True, type=Path, action="append")
    return parser


def _encoded(path: Path) -> str:
    return base64.b64encode(path.expanduser().resolve(strict=True).read_bytes()).decode("ascii")


async def main() -> None:
    args = _parser().parse_args()
    if len(args.bid) < 2:
        raise ValueError("Provide at least two --bid PDF paths.")
    workspace = await call_procurement_tool(
        "create_document_evaluation_workspace",
        {"title": "MCP client document evaluation"},
    )
    workspace_id = workspace["workspace_id"]
    await call_procurement_tool(
        "ingest_pdf_document",
        {
            "workspace_id": workspace_id,
            "filename": args.tender.name,
            "document_type": "TENDER_REQUIREMENTS",
            "pdf_base64": _encoded(args.tender),
        },
    )
    for bid in args.bid:
        await call_procurement_tool(
            "ingest_pdf_document",
            {
                "workspace_id": workspace_id,
                "filename": bid.name,
                "document_type": "SUPPLIER_BID",
                "pdf_base64": _encoded(bid),
            },
        )
    result = await call_procurement_tool(
        "run_document_agent_evaluation", {"workspace_id": workspace_id}
    )
    print(
        json.dumps(
            {
                "workspace_id": workspace_id,
                "evaluation_id": result["evaluation_id"],
                "status": result["status"],
                "supplier_count": len(result["suppliers"]),
                "review_priority": result["decision_support"]["review_priority"],
                "human_committee_required": result["human_committee_required"],
                "final_award_decision": result["final_award_decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
