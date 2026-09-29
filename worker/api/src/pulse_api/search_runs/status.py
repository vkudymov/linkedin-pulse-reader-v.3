from __future__ import annotations

from typing import Any

from .client_message import short_stored_error

LOST_MESSAGE = "Search session was lost after the worker restarted."
FAILED_MESSAGE = "Search failed."


def public_status_message(*, kind: str, status: str, error: str | None) -> str:
    if status == "running":
        return "Job search is running." if kind == "job" else "Post search is running."
    if status == "done":
        return "Job search completed." if kind == "job" else "Post search completed."
    if status == "lost":
        return LOST_MESSAGE
    return short_stored_error(error, fallback=FAILED_MESSAGE)


def resolve_polled_status(*, row: dict[str, Any], executor_alive: bool) -> dict[str, Any]:
    status = str(row.get("status") or "")
    persist_lost = status == "running" and not executor_alive
    if persist_lost:
        status = "lost"
    kind = str(row.get("kind") or "")
    error = row.get("error") if isinstance(row.get("error"), str) else None
    return {
        "run_id": str(row.get("id") or ""),
        "session_id": str(row.get("session_id") or ""),
        "status": status,
        "message": public_status_message(kind=kind, status=status, error=error),
        "persist_lost": persist_lost,
    }


def poll_search_run(
    *,
    user_id: str,
    session_id: str,
    executor_alive: bool,
    repo: Any | None = None,
) -> dict[str, str] | None:
    """
    Read ``search_runs`` by session id.

    Unknown session → None (caller returns 404).
    ``running`` without a live in-memory executor → persist ``lost`` and return it.
    If that update loses a race with a real finish, return the stored terminal status.
    """
    repository = repo if repo is not None else _repo()
    row = repository.get_by_session_id(user_id=user_id, session_id=session_id)
    if not isinstance(row, dict):
        return None

    view = resolve_polled_status(row=row, executor_alive=executor_alive)
    if view["persist_lost"]:
        updated = repository.mark_lost_if_running(run_id=view["run_id"], error=LOST_MESSAGE)
        if isinstance(updated, dict):
            view = resolve_polled_status(row=updated, executor_alive=True)
        else:
            fresh = repository.get_by_session_id(user_id=user_id, session_id=session_id)
            if not isinstance(fresh, dict):
                return None
            view = resolve_polled_status(row=fresh, executor_alive=True)

    return {
        "session_id": view["session_id"] or session_id,
        "status": str(view["status"]),
        "message": str(view["message"]),
    }


def _repo() -> Any:
    from ..deps.auth import _get_supabase_admin_client
    from storage.domain.pulse.search_runs import SearchRunRepository  # type: ignore[import-not-found]

    return SearchRunRepository(_get_supabase_admin_client())
