from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps.auth import _get_supabase_admin_client, require_user_id
from ..search_runs.helpers import start_people_search_session
from ..search_runs.status import poll_search_run
from .schemas import PeopleSearchRunResponse, PeopleSearchStartRequest
from .sessions import PeopleSearchSessionManager

router = APIRouter(prefix="/v1/people-search", tags=["people-search"])
_sessions = PeopleSearchSessionManager()


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


@router.post("/run", response_model=PeopleSearchRunResponse)
def start_run(
    req: PeopleSearchStartRequest,
    user_id: str = Depends(require_user_id),
) -> PeopleSearchRunResponse:
    _ensure_not_blocked(user_id=user_id)
    client = _get_supabase_admin_client()
    try:
        resp = (
            client.table("searches")
            .select("id,search_types!inner(code)")
            .eq("id", req.people_search_id)
            .eq("user_id", user_id)
            .eq("search_types.code", "people")
            .maybe_single()
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load people search."
        ) from e
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="People search not found.")

    sess = start_people_search_session(
        sessions=_sessions,
        user_id=user_id,
        people_search_id=req.people_search_id,
        limit=req.limit,
        account_label=req.account_label,
        initiated_by="user",
    )
    return PeopleSearchRunResponse(session_id=sess.session_id, status=sess.status, message=sess.message)


@router.get("/run/{session_id}", response_model=PeopleSearchRunResponse)
def get_status(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> PeopleSearchRunResponse:
    polled = poll_search_run(
        user_id=user_id,
        session_id=session_id,
        executor_alive=_sessions.owns(user_id=user_id, session_id=session_id),
    )
    if polled is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return PeopleSearchRunResponse(
        session_id=polled["session_id"],
        status=polled["status"],  # type: ignore[arg-type]
        message=polled["message"],
    )
