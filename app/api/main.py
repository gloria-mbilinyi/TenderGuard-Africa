"""Local TenderGuard API and authenticated browser backend-for-frontend.

The programmatic API keeps shared-key authentication. The dashboard uses a separate
server-side local session with HttpOnly cookies and CSRF protection. Neither interface
can approve reports or make procurement decisions.
"""

import os
from datetime import UTC, datetime
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Literal, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.agent.ollama_client import OllamaUnavailableError
from app.api.browser_auth import (
    BrowserSession,
    issue_browser_session,
    require_allowed_origin,
    require_browser_csrf,
    require_browser_session,
    revoke_browser_session,
    verify_dashboard_password,
)
from app.api.models import (
    BrowserLoginRequest,
    BrowserSessionResponse,
    CatalogResponse,
    EvaluationListResponse,
    EvaluationRequest,
    EvaluationResponse,
    ReportListResponse,
    SystemStatusResponse,
)
from app.services.catalog import CatalogSelectionError, load_catalog, validate_catalog_selection
from app.services.evaluation_store import list_evaluation_summaries, save_evaluation
from app.services.reports import list_generated_reports, resolve_generated_report
from app.services.system_status import configured_model, ollama_model_status

API_VERSION = "0.3.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(
    title="TenderGuard Africa API",
    version=API_VERSION,
    description="Local evaluation API; procurement decisions require human review.",
)


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


async def _execute_evaluation(request: EvaluationRequest) -> EvaluationResponse:
    validate_catalog_selection(request.tender_id, request.bid_id)

    from app.agent.workflow import procurement_agent

    state = await procurement_agent.ainvoke(
        {
            "tender_id": request.tender_id,
            "bid_id": request.bid_id,
            "status": "STARTED",
        }
    )

    if (
        state.get("status") != "AWAITING_HUMAN_REVIEW"
        or state.get("decision_support", {}).get("final_award_decision") is not None
    ):
        raise RuntimeError("Evaluation did not reach the required human-review state.")

    support = dict(state.get("decision_support", {}))
    support["human_committee_required"] = True
    support["final_award_decision"] = None
    evaluation = EvaluationResponse(
        evaluation_id=str(uuid4()),
        completed_at=datetime.now(UTC).isoformat(),
        tender_id=request.tender_id,
        bid_id=request.bid_id,
        status="AWAITING_HUMAN_REVIEW",
        completed_tools=state.get("completed_tools", []),
        decision_support=support,
        tender=state.get("tender"),
        compliance=state.get("compliance"),
        price_analysis=state.get("price_analysis"),
        supplier_risk=state.get("supplier_risk"),
    )
    save_evaluation(evaluation.model_dump(mode="json"))
    return evaluation


async def _evaluation_with_http_errors(request: EvaluationRequest) -> EvaluationResponse:
    try:
        return await _execute_evaluation(request)
    except CatalogSelectionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI workflow returned an invalid structured response.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Evaluation unavailable; check local Ollama and procurement MCP services.",
        ) from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tenderguard-africa", "version": API_VERSION}


@app.post(
    "/api/evaluations",
    response_model=EvaluationResponse,
    dependencies=[Depends(require_local_api_key)],
)
async def evaluate_bid(request: EvaluationRequest) -> EvaluationResponse:
    return await _evaluation_with_http_errors(request)


@app.post("/api/browser/session", response_model=BrowserSessionResponse)
def browser_login(
    request: Request,
    response: Response,
    credentials: BrowserLoginRequest,
) -> BrowserSessionResponse:
    require_allowed_origin(request)
    verify_dashboard_password(credentials.password)
    return issue_browser_session(response)


@app.get("/api/browser/session", response_model=BrowserSessionResponse)
def browser_session(
    session: Annotated[BrowserSession, Depends(require_browser_session)],
) -> BrowserSessionResponse:
    return BrowserSessionResponse(
        csrf_token=session.csrf_token,
        expires_at=datetime.fromtimestamp(session.expires_at, UTC).isoformat(),
    )


@app.post("/api/browser/logout", status_code=status.HTTP_204_NO_CONTENT)
def browser_logout(
    response: Response,
    session: Annotated[BrowserSession, Depends(require_browser_csrf)],
) -> Response:
    revoke_browser_session(response, session)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.get("/api/browser/catalog", response_model=CatalogResponse)
def browser_catalog(
    session: Annotated[BrowserSession, Depends(require_browser_session)],
) -> CatalogResponse:
    del session
    return CatalogResponse.model_validate(load_catalog())


@app.post("/api/browser/evaluations", response_model=EvaluationResponse)
async def browser_evaluate_bid(
    request: EvaluationRequest,
    session: Annotated[BrowserSession, Depends(require_browser_csrf)],
) -> EvaluationResponse:
    del session
    return await _evaluation_with_http_errors(request)


@app.get("/api/browser/evaluations", response_model=EvaluationListResponse)
def browser_evaluations(
    session: Annotated[BrowserSession, Depends(require_browser_session)],
) -> EvaluationListResponse:
    del session
    return EvaluationListResponse(evaluations=list_evaluation_summaries())


@app.get("/api/browser/reports", response_model=ReportListResponse)
def browser_reports(
    session: Annotated[BrowserSession, Depends(require_browser_session)],
) -> ReportListResponse:
    del session
    return ReportListResponse(reports=list_generated_reports())


@app.get("/api/browser/reports/{filename}/download", response_class=FileResponse)
def browser_report_download(
    filename: str,
    session: Annotated[BrowserSession, Depends(require_browser_session)],
) -> FileResponse:
    del session
    try:
        report_path = resolve_generated_report(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(
        report_path,
        media_type="text/markdown; charset=utf-8",
        filename=report_path.name,
    )


@app.get("/api/browser/system", response_model=SystemStatusResponse)
async def browser_system_status(
    session: Annotated[BrowserSession, Depends(require_browser_session)],
) -> SystemStatusResponse:
    del session
    model_status = cast(
        Literal["AVAILABLE", "MODEL_MISSING", "UNAVAILABLE"],
        await ollama_model_status(),
    )
    return SystemStatusResponse(
        api_version=API_VERSION,
        model=configured_model(),
        model_status=model_status,
    )


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="dashboard")
