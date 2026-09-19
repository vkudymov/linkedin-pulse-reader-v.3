from __future__ import annotations

from typing import Any, Literal

from ..deps.auth import _get_supabase_admin_client

InitiatedBy = Literal["user", "admin"]


def _repo() -> Any:
    from storage.domain.pulse.search_runs import SearchRunRepository  # type: ignore[import-not-found]

    return SearchRunRepository(_get_supabase_admin_client())


def create_post_search_run(
    *,
    user_id: str,
    post_search_id: str,
    limit: int,
    account_label: str | None,
    initiated_by: InitiatedBy = "user",
    admin_actor_id: str | None = None,
) -> str:
    client = _get_supabase_admin_client()
    resp = (
        client.table("post_searches")
        .select("id,title,search_prompt,comment_prompt,account_label")
        .eq("id", post_search_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise ValueError("post_search not found")

    label = account_label if account_label else (
        row.get("account_label") if isinstance(row.get("account_label"), str) else None
    )
    created = _repo().create_running(
        user_id=user_id,
        kind="post",
        post_search_id=post_search_id,
        search_title=str(row.get("title") or "Post search"),
        limit_count=limit,
        account_label=label,
        search_prompt=str(row.get("search_prompt") or ""),
        comment_prompt=row.get("comment_prompt") if isinstance(row.get("comment_prompt"), str) else None,
        initiated_by=initiated_by,
        admin_actor_id=admin_actor_id,
    )
    return str(created["id"])


def create_job_search_run(
    *,
    user_id: str,
    job_search_id: str,
    limit: int,
    account_label: str | None,
    initiated_by: InitiatedBy = "user",
    admin_actor_id: str | None = None,
) -> str:
    client = _get_supabase_admin_client()
    resp = (
        client.table("job_searches")
        .select(
            "id,title,search_query,location,filter_prompt,linkedin_filters"
        )
        .eq("id", job_search_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise ValueError("job_search not found")

    filters = row.get("linkedin_filters") if isinstance(row.get("linkedin_filters"), dict) else None
    created = _repo().create_running(
        user_id=user_id,
        kind="job",
        job_search_id=job_search_id,
        search_title=str(row.get("title") or "Job search"),
        limit_count=limit,
        account_label=account_label,
        search_query=str(row.get("search_query") or ""),
        location=row.get("location") if isinstance(row.get("location"), str) else None,
        linkedin_filters=filters,
        filter_prompt=str(row.get("filter_prompt") or ""),
        initiated_by=initiated_by,
        admin_actor_id=admin_actor_id,
    )
    return str(created["id"])


def attach_session_id(*, run_id: str, session_id: str) -> None:
    _repo().set_session_id(run_id=run_id, session_id=session_id)


def finalize_run_error(*, run_id: str | None, error: str | None) -> None:
    if not run_id:
        return
    _repo().finalize_if_running(run_id=run_id, status="error", error=error)
