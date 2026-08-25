from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import require_user_id
from .schemas import PostSearchRunResponse, PostSearchStartRequest
from .sessions import PostSearchSessionManager

router = APIRouter(prefix="/v1/post-search", tags=["post-search"])
_sessions = PostSearchSessionManager()


@router.post("/run", response_model=PostSearchRunResponse)
def start_run(
    req: PostSearchStartRequest,
    user_id: str = Depends(require_user_id),
) -> PostSearchRunResponse:
    sess = _sessions.start(user_id=user_id, limit=req.limit, account_label=req.account_label)
    return PostSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


@router.get("/run/{session_id}", response_model=PostSearchRunResponse)
def get_status(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> PostSearchRunResponse:
    sess = _sessions.get(user_id=user_id, session_id=session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return PostSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)

