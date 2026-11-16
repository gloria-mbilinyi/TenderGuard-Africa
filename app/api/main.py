"""Local-only API prototype for the TenderGuard evaluation workflow.

This API has deliberately no report approval or award action. Its temporary
shared-key protection is not a substitute for production user authentication.
"""

import os
from hmac import compare_digest
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.agent.ollama_client import OllamaUnavailableError

app = FastAPI(
    title="TenderGuard Africa API",
    version="0.2.0",
    description="Local evaluation API; procurement decisions require human review.",
)


class EvaluationRequest(BaseModel):
    tender_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    bid_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class EvaluationResponse(BaseModel):
    tender_id: str
    bid_id: str
    status: Literal["AWAITING_HUMAN_REVIEW"]
    completed_tools: list[str]
    decision_support: dict[str, Any]
    human_committee_required: Literal[True] = True
    final_award_decision: None = None


def require_local_api_key(x_tenderguard_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("TENDERGUARD_API_KEY", "")
    if len(expected) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Set TENDERGUARD_API_KEY to a private value of at least 32 characters.",
        )
    if not x_tenderguard_key or not compare_digest(x_tenderguard_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tenderguard-africa"}


@app.post(
    "/api/evaluations",
    response_model=EvaluationResponse,
    dependencies=[Depends(require_local_api_key)],
)
async def evaluate_bid(request: EvaluationRequest) -> EvaluationResponse:
    # Import lazily so /api/health remains available without an Ollama process.
    try:
        from app.agent.workflow import procurement_agent

        state = await procurement_agent.ainvoke(
            {
                "tender_id": request.tender_id,
                "bid_id": request.bid_id,
                "status": "STARTED",
            }
        )
    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Evaluation unavailable; check local Ollama and procurement MCP services.",
        ) from exc

    if (
        state.get("status") != "AWAITING_HUMAN_REVIEW"
        or state.get("decision_support", {}).get("final_award_decision") is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation did not reach the required human-review state.",
        )

    # Do not expose raw tender documents or internal MCP logs in API responses.
    support = dict(state.get("decision_support", {}))
    support["human_committee_required"] = True
    support["final_award_decision"] = None
    return EvaluationResponse(
        tender_id=request.tender_id,
        bid_id=request.bid_id,
        status="AWAITING_HUMAN_REVIEW",
        completed_tools=state.get("completed_tools", []),
        decision_support=support,
    )
