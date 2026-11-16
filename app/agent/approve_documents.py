"""CLI-only authorization gate for uploaded-document draft report generation."""

import argparse
import asyncio
import json

from app.agent.mcp_client import call_procurement_tool


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Authorize a draft report for a completed PDF document evaluation."
    )
    parser.add_argument("--workspace", required=True, help="Document workspace identifier")
    parser.add_argument(
        "--approved-by",
        required=True,
        help="Name of the human reviewer authorizing draft report generation",
    )
    return parser


async def _run(workspace_id: str, approved_by: str) -> dict[str, object]:
    return await call_procurement_tool(
        "generate_document_evaluation_report",
        {"workspace_id": workspace_id, "approved_by": approved_by},
    )


def main() -> None:
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(_run(args.workspace, args.approved_by)), indent=2))


if __name__ == "__main__":
    main()
