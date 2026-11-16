"""LangGraph workflow for page-cited evaluation of uploaded procurement PDFs."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.agent.mcp_client import call_procurement_tool
from app.agent.ollama_client import plan_document_evaluation, synthesize_document_evidence


class DocumentEvaluationState(TypedDict, total=False):
    workspace_id: str
    plan: list[str]
    plan_rationale: str
    completed_tools: list[str]
    workspace_evidence: dict[str, Any]
    document_evaluation: dict[str, Any]
    decision_support: dict[str, Any]
    status: str


async def plan_node(state: DocumentEvaluationState) -> dict[str, Any]:
    plan = await plan_document_evaluation(state["workspace_id"])
    return {
        "plan": plan.tool_sequence,
        "plan_rationale": plan.rationale,
        "completed_tools": [],
        "status": "PLANNED_BY_OPEN_MODEL",
    }


def _completed(state: DocumentEvaluationState, tool_name: str) -> list[str]:
    return [*state.get("completed_tools", []), tool_name]


async def load_node(state: DocumentEvaluationState) -> dict[str, Any]:
    result = await call_procurement_tool(
        "load_document_workspace", {"workspace_id": state["workspace_id"]}
    )
    return {
        "workspace_evidence": result,
        "completed_tools": _completed(state, "load_document_workspace"),
        "status": "DOCUMENTS_LOADED",
    }


async def evaluate_node(state: DocumentEvaluationState) -> dict[str, Any]:
    result = await call_procurement_tool(
        "evaluate_document_workspace", {"workspace_id": state["workspace_id"]}
    )
    return {
        "document_evaluation": result,
        "completed_tools": _completed(state, "evaluate_document_workspace"),
        "status": "DOCUMENTS_EVALUATED",
    }


async def synthesize_node(state: DocumentEvaluationState) -> dict[str, Any]:
    result = await synthesize_document_evidence(state["document_evaluation"])
    return {
        "decision_support": result.model_dump(),
        "status": "AWAITING_HUMAN_REVIEW",
    }


def route_next(state: DocumentEvaluationState) -> str:
    for tool_name in state["plan"]:
        if tool_name not in state.get("completed_tools", []):
            return tool_name
    return "synthesize"


retry_policy = RetryPolicy(max_attempts=2)
builder = StateGraph(DocumentEvaluationState)
builder.add_node("plan", plan_node)
builder.add_node("load_document_workspace", load_node, retry_policy=retry_policy)
builder.add_node("evaluate_document_workspace", evaluate_node, retry_policy=retry_policy)
builder.add_node("synthesize", synthesize_node)
builder.add_edge(START, "plan")
for node_name in ["plan", "load_document_workspace", "evaluate_document_workspace"]:
    builder.add_conditional_edges(
        node_name,
        route_next,
        {
            "load_document_workspace": "load_document_workspace",
            "evaluate_document_workspace": "evaluate_document_workspace",
            "synthesize": "synthesize",
        },
    )
builder.add_edge("synthesize", END)

document_procurement_agent = builder.compile(name="TenderGuard Document Procurement Agent")
