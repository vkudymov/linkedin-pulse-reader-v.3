from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import require_user_id
from .schemas import LoginSessionResponse, LoginStartRequest
from .sessions import LoginSessionManager


router = APIRouter(prefix="/v1/linkedin", tags=["linkedin"])
_sessions = LoginSessionManager()


@router.post("/login", response_model=LoginSessionResponse)
def start_login(
    req: LoginStartRequest,
    user_id: str = Depends(require_user_id),
) -> LoginSessionResponse:
    sess = _sessions.start(
        user_id=user_id,
        method=req.method,
        identifier=req.identifier,
        password=req.password,
        label=req.label,
    )
    return LoginSessionResponse(
        session_id=sess.session_id,
        status=sess.status,
        message=sess.message,
        linkedin_account_id=sess.linkedin_account_id,
    )


@router.get("/login/{session_id}", response_model=LoginSessionResponse)
def get_login_status(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> LoginSessionResponse:
    sess = _sessions.get(user_id=user_id, session_id=session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return LoginSessionResponse(
        session_id=sess.session_id,
        status=sess.status,
        message=sess.message,
        linkedin_account_id=sess.linkedin_account_id,
    )


@router.delete("/login/{session_id}", response_model=LoginSessionResponse)
def cancel_login(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> LoginSessionResponse:
    sess = _sessions.cancel(user_id=user_id, session_id=session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return LoginSessionResponse(
        session_id=sess.session_id,
        status=sess.status,
        message=sess.message,
        linkedin_account_id=sess.linkedin_account_id,
    )

