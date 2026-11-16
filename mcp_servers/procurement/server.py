import asyncio
import base64
import binascii
from typing import Any, Literal

from mcp.server import MCPServer

from app.agent.document_runner import execute_document_evaluation
from app.services.document_store import (
    add_pdf_document,
    create_workspace,
    load_evaluation_result,
    load_workspace,
)
from mcp_servers.procurement.audit import execute_logged
from mcp_servers.procurement.tools.check_bid_compliance import (
    check_bid_compliance_record,
)
from mcp_servers.procurement.tools.compare_prices import compare_bid_price
from mcp_servers.procurement.tools.document_evaluation import (
    evaluate_document_workspace as evaluate_document_workspace_record,
)
from mcp_servers.procurement.tools.document_evaluation import (
    load_document_workspace_evidence,
)
from mcp_servers.procurement.tools.flag_supplier_risk import (
    flag_supplier_risk_record,
)
from mcp_servers.procurement.tools.generate_document_report import (
    generate_document_evaluation_report_file,
)
from mcp_servers.procurement.tools.generate_evaluation_report import (
    generate_evaluation_report_file,
)
from mcp_servers.procurement.tools.load_tender import load_tender_record

mcp = MCPServer("TenderGuard Procurement MCP")


@mcp.tool()
def create_document_evaluation_workspace(title: str = "Uploaded procurement evaluation") -> dict[str, Any]:
    """Create an isolated workspace for one tender PDF and multiple supplier bids."""

    return execute_logged(
        tool_name="create_document_evaluation_workspace",
        inputs={"title": title[:200]},
        action=lambda: create_workspace(title),
    )


@mcp.tool()
def ingest_pdf_document(
    workspace_id: str,
    filename: str,
    document_type: Literal["TENDER_REQUIREMENTS", "SUPPLIER_BID"],
    pdf_base64: str,
    supplier_name: str | None = None,
) -> dict[str, Any]:
    """Validate, store, and text-extract one base64-encoded searchable PDF."""

    try:
        content = base64.b64decode(pdf_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("pdf_base64 must contain valid base64-encoded PDF bytes.") from exc
    return execute_logged(
        tool_name="ingest_pdf_document",
        inputs={
            "workspace_id": workspace_id,
            "filename": filename,
            "document_type": document_type,
            "size_bytes": len(content),
        },
        action=lambda: add_pdf_document(
            workspace_id,
            filename=filename,
            content_type="application/pdf",
            document_type=document_type,
            content=content,
            supplier_name=supplier_name,
        ),
    )


@mcp.tool()
def get_document_evaluation_status(workspace_id: str) -> dict[str, Any]:
    """Return safe workspace status without PDF bytes or server paths."""

    return execute_logged(
        tool_name="get_document_evaluation_status",
        inputs={"workspace_id": workspace_id},
        action=lambda: load_workspace(workspace_id, include_previews=False),
    )


@mcp.tool()
def get_document_evaluation_result(workspace_id: str) -> dict[str, Any]:
    """Return a completed page-cited evaluation that is awaiting human review."""

    return execute_logged(
        tool_name="get_document_evaluation_result",
        inputs={"workspace_id": workspace_id},
        action=lambda: load_evaluation_result(workspace_id),
    )


@mcp.tool()
def run_document_agent_evaluation(workspace_id: str) -> dict[str, Any]:
    """Run the real LangGraph, Procurement MCP, and Ollama document evaluation."""

    result = asyncio.run(execute_document_evaluation(workspace_id))
    return result.model_dump(mode="json")


@mcp.tool()
def load_tender(tender_id: str) -> dict[str, Any]:
    """Load and normalize a tender record with source information."""

    return execute_logged(
        tool_name="load_tender",
        inputs={"tender_id": tender_id},
        action=lambda: load_tender_record(tender_id),
    )


@mcp.tool()
def check_bid_compliance(
    tender_id: str,
    bid_id: str,
) -> dict[str, Any]:
    """Check a bid against mandatory tender requirements."""

    return execute_logged(
        tool_name="check_bid_compliance",
        inputs={
            "tender_id": tender_id,
            "bid_id": bid_id,
        },
        action=lambda: check_bid_compliance_record(
            tender_id,
            bid_id,
        ),
    )


@mcp.tool()
def compare_prices(bid_id: str) -> dict[str, Any]:
    """Compare bid price with historical award values."""

    return execute_logged(
        tool_name="compare_prices",
        inputs={"bid_id": bid_id},
        action=lambda: compare_bid_price(bid_id),
    )


@mcp.tool()
def flag_supplier_risk(bid_id: str) -> dict[str, Any]:
    """Flag sourced supplier-data inconsistencies for human review."""

    return execute_logged(
        tool_name="flag_supplier_risk",
        inputs={"bid_id": bid_id},
        action=lambda: flag_supplier_risk_record(bid_id),
    )


@mcp.tool()
def load_document_workspace(workspace_id: str) -> dict[str, Any]:
    """Load metadata for one isolated uploaded-document evaluation workspace."""

    return execute_logged(
        tool_name="load_document_workspace",
        inputs={"workspace_id": workspace_id},
        action=lambda: load_document_workspace_evidence(workspace_id),
    )


@mcp.tool()
def evaluate_document_workspace(workspace_id: str) -> dict[str, Any]:
    """Evaluate one tender PDF and at least two bid PDFs with page citations."""

    return execute_logged(
        tool_name="evaluate_document_workspace",
        inputs={"workspace_id": workspace_id},
        action=lambda: evaluate_document_workspace_record(workspace_id),
    )


@mcp.tool()
def generate_evaluation_report(
    tender_id: str,
    bid_id: str,
    approved_by: str,
) -> dict[str, Any]:
    """Generate a draft report after named human approval."""

    return execute_logged(
        tool_name="generate_evaluation_report",
        inputs={
            "tender_id": tender_id,
            "bid_id": bid_id,
        },
        human_approver=approved_by,
        action=lambda: generate_evaluation_report_file(
            tender_id,
            bid_id,
            approved_by,
        ),
    )


@mcp.tool()
def generate_document_evaluation_report(
    workspace_id: str,
    approved_by: str,
) -> dict[str, Any]:
    """Generate a draft uploaded-document report after named human approval."""

    return execute_logged(
        tool_name="generate_document_evaluation_report",
        inputs={"workspace_id": workspace_id},
        human_approver=approved_by,
        action=lambda: generate_document_evaluation_report_file(workspace_id, approved_by),
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
