from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import _get_supabase_admin_client, require_user_id
from .schemas import PostSearchRunResponse, PostSearchStartRequest
from .sessions import PostSearchSessionManager

router = APIRouter(prefix="/v1/post-search", tags=["post-search"])
_sessions = PostSearchSessionManager()


def _ensure_not_blocked_and_increment_counter(*, user_id: str) -> None:
    client = _get_supabase_admin_client()
    try:
        prof_resp = (
            client.table("user_admin_state")
            .select("is_blocked,post_search_run_count")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Profile check failed.") from e

    row = getattr(prof_resp, "data", None)
    is_blocked = bool(row.get("is_blocked")) if isinstance(row, dict) else False
    if is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь заблокирован.")

    prev = int(row.get("post_search_run_count") or 0) if isinstance(row, dict) else 0
    try:
        client.table("user_admin_state").update(
            {"post_search_run_count": prev + 1}
        ).eq("id", user_id).execute()
    except Exception:
        # Best-effort counter; do not block post search.
        return


@router.post("/run", response_model=PostSearchRunResponse)
def start_run(
    req: PostSearchStartRequest,
    user_id: str = Depends(require_user_id),
) -> PostSearchRunResponse:
    _ensure_not_blocked_and_increment_counter(user_id=user_id)
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

