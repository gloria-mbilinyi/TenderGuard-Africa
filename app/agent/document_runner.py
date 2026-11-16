"""Shared execution service for uploaded-document LangGraph evaluations."""

from datetime import UTC, datetime
from uuid import uuid4

from app.api.models import DocumentEvaluationResponse
from app.services.document_store import (
    DocumentStoreError,
    load_workspace,
    save_evaluation_result,
)


async def execute_document_evaluation(workspace_id: str) -> DocumentEvaluationResponse:
    from app.agent.document_workflow import document_procurement_agent

    workspace = load_workspace(workspace_id, include_previews=False)
    if workspace["status"] not in {"READY_FOR_EVALUATION", "AWAITING_HUMAN_REVIEW"}:
        raise DocumentStoreError(
            "Upload exactly one tender requirements PDF and at least two supplier bid PDFs."
        )
    state = await document_procurement_agent.ainvoke(
        {"workspace_id": workspace_id, "status": "STARTED"}
    )
    if (
        state.get("status") != "AWAITING_HUMAN_REVIEW"
        or state.get("decision_support", {}).get("final_award_decision") is not None
    ):
        raise RuntimeError("Document evaluation did not reach the required review state.")
    evidence = state.get("document_evaluation") or {}
    result = DocumentEvaluationResponse(
        evaluation_id=str(uuid4()),
        workspace_id=workspace_id,
        completed_at=datetime.now(UTC).isoformat(),
        status="AWAITING_HUMAN_REVIEW",
        completed_tools=state.get("completed_tools", []),
        tender=evidence.get("tender"),
        suppliers=evidence.get("suppliers", []),
        comparison=evidence.get("comparison"),
        decision_support=state.get("decision_support"),
    )
    save_evaluation_result(workspace_id, result.model_dump(mode="json"))
    return result
