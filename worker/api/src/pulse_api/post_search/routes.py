from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import _get_supabase_admin_client, require_user_id
from ..search_quota import SearchQuotaError, charge_post_search_quota_after_start, raise_for_quota
from ..search_runs.helpers import start_post_search_session
from ..search_runs.status import poll_search_run
from .schemas import PostSearchRunResponse, PostSearchStartRequest
from .sessions import PostSearchSessionManager

router = APIRouter(prefix="/v1/post-search", tags=["post-search"])
_sessions = PostSearchSessionManager()


def _ensure_not_blocked(*, user_id: str) -> None:
    client = _get_supabase_admin_client()
    try:
        prof_resp = (
            client.table("user_admin_state")
            .select("is_blocked")
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


@router.post("/run", response_model=PostSearchRunResponse)
def start_run(
    req: PostSearchStartRequest,
    user_id: str = Depends(require_user_id),
) -> PostSearchRunResponse:
    _ensure_not_blocked(user_id=user_id)
    client = _get_supabase_admin_client()
    try:
        resp = (
            client.table("searches")
            .select("id,search_types!inner(code)")
            .eq("id", req.post_search_id)
            .eq("user_id", user_id)
            .eq("search_types.code", "posts")
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load post search.") from e
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post search not found.")

    try:
        sess = charge_post_search_quota_after_start(
            client=client,
            user_id=user_id,
            start=lambda: start_post_search_session(
                sessions=_sessions,
                user_id=user_id,
                post_search_id=req.post_search_id,
                limit=req.limit,
                account_label=req.account_label,
                initiated_by="user",
            ),
        )
    except SearchQuotaError as exc:
        raise_for_quota(exc)
    return PostSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


@router.get("/run/{session_id}", response_model=PostSearchRunResponse)
def get_status(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> PostSearchRunResponse:
    polled = poll_search_run(
        user_id=user_id,
        session_id=session_id,
        executor_alive=_sessions.owns(user_id=user_id, session_id=session_id),
    )
    if polled is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return PostSearchRunResponse(
        session_id=polled["session_id"],
        status=polled["status"],
        message=polled["message"],
    )

