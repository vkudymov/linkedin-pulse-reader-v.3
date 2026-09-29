from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import _get_supabase_admin_client, require_user_id
from ..search_runs.helpers import start_job_search_session
from ..search_runs.status import poll_search_run
from .schemas import JobSearchRunResponse, JobSearchStartRequest
from .sessions import JobSearchSessionManager

router = APIRouter(prefix="/v1/job-search", tags=["job-search"])
_sessions = JobSearchSessionManager()


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile check failed.",
        ) from e

    row = getattr(prof_resp, "data", None)
    is_blocked = bool(row.get("is_blocked")) if isinstance(row, dict) else False
    if is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь заблокирован.")


@router.post("/run", response_model=JobSearchRunResponse)
def start_run(
    req: JobSearchStartRequest,
    user_id: str = Depends(require_user_id),
) -> JobSearchRunResponse:
    _ensure_not_blocked(user_id=user_id)
    client = _get_supabase_admin_client()
    try:
        resp = (
            client.table("searches")
            .select("id,search_types!inner(code)")
            .eq("id", req.job_search_id)
            .eq("user_id", user_id)
            .eq("search_types.code", "jobs")
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load job search.") from e
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job search not found.")

    sess = start_job_search_session(
        sessions=_sessions,
        user_id=user_id,
        job_search_id=req.job_search_id,
        limit=req.limit,
        account_label=req.account_label,
        initiated_by="user",
    )
    return JobSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


@router.get("/run/{session_id}", response_model=JobSearchRunResponse)
def get_status(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> JobSearchRunResponse:
    polled = poll_search_run(
        user_id=user_id,
        session_id=session_id,
        executor_alive=_sessions.owns(user_id=user_id, session_id=session_id),
    )
    if polled is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return JobSearchRunResponse(
        session_id=polled["session_id"],
        status=polled["status"],  # type: ignore[arg-type]
        message=polled["message"],
    )

