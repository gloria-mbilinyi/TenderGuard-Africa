import os
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from hmac import compare_digest
from threading import Lock
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status

from app.api.models import BrowserSessionResponse

SESSION_COOKIE_NAME = "tenderguard_session"
SESSION_LIFETIME_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class BrowserSession:
    session_id: str
    csrf_token: str
    expires_at: float


_sessions: dict[str, BrowserSession] = {}
_session_lock = Lock()


def _dashboard_password() -> str:
    return os.getenv("TENDERGUARD_DASHBOARD_PASSWORD", "")


def _allowed_origins() -> set[str]:
    configured = os.getenv("TENDERGUARD_ALLOWED_ORIGINS", "")
    if configured.strip():
        return {origin.strip() for origin in configured.split(",") if origin.strip()}
    return {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }


def require_allowed_origin(request: Request) -> None:
    origin = request.headers.get("origin", "")
    if origin not in _allowed_origins():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin is not allowed for the local dashboard.",
        )


def verify_dashboard_password(password: str) -> None:
    expected = _dashboard_password()
    if len(expected) < 12:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Set TENDERGUARD_DASHBOARD_PASSWORD to a private value of at least "
                "12 characters before using the dashboard."
            ),
        )
    if not compare_digest(password, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard credentials.",
        )


def _delete_expired_sessions(now: float) -> None:
    expired = [session_id for session_id, value in _sessions.items() if value.expires_at <= now]
    for session_id in expired:
        _sessions.pop(session_id, None)


def issue_browser_session(response: Response) -> BrowserSessionResponse:
    now = time.time()
    session = BrowserSession(
        session_id=secrets.token_urlsafe(32),
        csrf_token=secrets.token_urlsafe(32),
        expires_at=now + SESSION_LIFETIME_SECONDS,
    )
    with _session_lock:
        _delete_expired_sessions(now)
        _sessions[session.session_id] = session

    cookie_secure = os.getenv("TENDERGUARD_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.session_id,
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=cookie_secure,
        samesite="strict",
        path="/api/browser",
    )
    return BrowserSessionResponse(
        csrf_token=session.csrf_token,
        expires_at=datetime.fromtimestamp(session.expires_at, UTC).isoformat(),
    )


def require_browser_session(
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> BrowserSession:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dashboard sign-in required.",
        )
    now = time.time()
    with _session_lock:
        _delete_expired_sessions(now)
        session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dashboard session is missing or expired.",
        )
    return session


def require_browser_csrf(
    request: Request,
    session: Annotated[BrowserSession, Depends(require_browser_session)],
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> BrowserSession:
    require_allowed_origin(request)
    if not csrf_token or not compare_digest(csrf_token, session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid CSRF token.",
        )
    return session


def revoke_browser_session(response: Response, session: BrowserSession) -> None:
    with _session_lock:
        _sessions.pop(session.session_id, None)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/api/browser",
        httponly=True,
        samesite="strict",
    )


def reset_browser_sessions_for_tests() -> None:
    with _session_lock:
        _sessions.clear()
