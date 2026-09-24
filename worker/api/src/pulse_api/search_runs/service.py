from __future__ import annotations

from typing import Any, Literal, TypedDict

from ..deps.auth import _get_supabase_admin_client

InitiatedBy = Literal["user", "admin"]


class TariffParams(TypedDict):
    id: str
    max_scan_count: int
    target_found_count: int
    min_relevance_percent: int


DEFAULT_POST_SCAN = 10
DEFAULT_JOB_SCAN = 25


def resolve_run_limits(
    *,
    tariff: TariffParams | None,
    kind: Literal["post", "job"],
    request_limit: int | None = None,
) -> tuple[int, int, int]:
    """Return (max_scan, target_found, min_score). Tariff wins; else request/default."""
    default_scan = DEFAULT_POST_SCAN if kind == "post" else DEFAULT_JOB_SCAN
    if tariff:
        return (
            int(tariff["max_scan_count"]),
            int(tariff["target_found_count"]),
            int(tariff["min_relevance_percent"]),
        )
    scan = int(request_limit) if request_limit and request_limit > 0 else default_scan
    return scan, max(1, scan), 0


def _repo() -> Any:
    from storage.domain.pulse.search_runs import SearchRunRepository  # type: ignore[import-not-found]

    return SearchRunRepository(_get_supabase_admin_client())

def _as_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _resolve_tariff_params(*, client: Any, tariff_id: Any) -> TariffParams | None:
    row: dict[str, Any] | None = None
    if isinstance(tariff_id, str) and tariff_id:
        resp = (
            client.table("search_tariffs")
            .select("id,max_scan_count,target_found_count,min_relevance_percent")
            .eq("id", tariff_id)
            .maybe_single()
            .execute()
        )
        data = getattr(resp, "data", None)
        row = data if isinstance(data, dict) else None
    if not row:
        resp = (
            client.table("search_tariffs")
            .select("id,max_scan_count,target_found_count,min_relevance_percent")
            .order("sort_order", desc=False)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        data = getattr(resp, "data", None)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            row = data[0]
        elif isinstance(data, dict):
            row = data
    if not row:
        return None
    tid = str(row.get("id") or "")
    if not tid:
        return None
    return {
        "id": tid,
        "max_scan_count": max(1, min(500, _as_int(row.get("max_scan_count"), 25))),
        "target_found_count": max(1, min(500, _as_int(row.get("target_found_count"), 10))),
        "min_relevance_percent": max(0, min(100, _as_int(row.get("min_relevance_percent"), 0))),
    }


def create_post_search_run(
    *,
    user_id: str,
    post_search_id: str,
    limit: int | None,
    account_label: str | None,
    initiated_by: InitiatedBy = "user",
    admin_actor_id: str | None = None,
) -> tuple[str, TariffParams | None]:
    client = _get_supabase_admin_client()
    resp = (
        client.table("searches")
        .select(
            "id,title,account_label,search_tariff_id,search_types!inner(code),"
            "search_prompt:prompts!searches_search_prompt_id_fkey(body),"
            "comment_prompt:prompts!searches_comment_prompt_id_fkey(body)"
        )
        .eq("id", post_search_id)
        .eq("user_id", user_id)
        .eq("search_types.code", "posts")
        .maybe_single()
        .execute()
    )
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise ValueError("post_search not found")

    label = account_label if account_label else (
        row.get("account_label") if isinstance(row.get("account_label"), str) else None
    )
    search_prompt = ""
    comment_prompt = None
    sp = row.get("search_prompt")
    cp = row.get("comment_prompt")
    if isinstance(sp, dict) and isinstance(sp.get("body"), str):
        search_prompt = str(sp.get("body") or "")
    if isinstance(cp, dict) and isinstance(cp.get("body"), str):
        comment_prompt = str(cp.get("body") or "") or None
    if not search_prompt:
        raise ValueError("post_search prompt not found")
    tariff = _resolve_tariff_params(client=client, tariff_id=row.get("search_tariff_id"))
    scan_limit, _, _ = resolve_run_limits(tariff=tariff, kind="post", request_limit=limit)
    created = _repo().create_running(
        user_id=user_id,
        kind="post",
        search_id=post_search_id,
        search_title=str(row.get("title") or "Post search"),
        limit_count=scan_limit,
        account_label=label,
        search_prompt=search_prompt,
        comment_prompt=comment_prompt,
        initiated_by=initiated_by,
        admin_actor_id=admin_actor_id,
    )
    return str(created["id"]), tariff


def create_job_search_run(
    *,
    user_id: str,
    job_search_id: str,
    limit: int | None,
    account_label: str | None,
    initiated_by: InitiatedBy = "user",
    admin_actor_id: str | None = None,
) -> tuple[str, TariffParams | None]:
    client = _get_supabase_admin_client()
    resp = (
        client.table("searches")
        .select(
            "id,title,search_query,location,linkedin_filters,search_tariff_id,search_types!inner(code),"
            "filter_prompt:prompts!searches_filter_prompt_id_fkey(body)"
        )
        .eq("id", job_search_id)
        .eq("user_id", user_id)
        .eq("search_types.code", "jobs")
        .maybe_single()
        .execute()
    )
    row = getattr(resp, "data", None)
    if not isinstance(row, dict) or not row.get("id"):
        raise ValueError("job_search not found")

    filters = row.get("linkedin_filters") if isinstance(row.get("linkedin_filters"), dict) else None
    filter_prompt = ""
    fp = row.get("filter_prompt")
    if isinstance(fp, dict) and isinstance(fp.get("body"), str):
        filter_prompt = str(fp.get("body") or "")
    if not filter_prompt:
        raise ValueError("job_search filter_prompt not found")
    tariff = _resolve_tariff_params(client=client, tariff_id=row.get("search_tariff_id"))
    scan_limit, _, _ = resolve_run_limits(tariff=tariff, kind="job", request_limit=limit)
    created = _repo().create_running(
        user_id=user_id,
        kind="job",
        search_id=job_search_id,
        search_title=str(row.get("title") or "Job search"),
        limit_count=scan_limit,
        account_label=account_label,
        search_query=str(row.get("search_query") or ""),
        location=row.get("location") if isinstance(row.get("location"), str) else None,
        linkedin_filters=filters,
        filter_prompt=filter_prompt,
        initiated_by=initiated_by,
        admin_actor_id=admin_actor_id,
    )
    return str(created["id"]), tariff


def attach_session_id(*, run_id: str, session_id: str) -> None:
    _repo().set_session_id(run_id=run_id, session_id=session_id)


def finalize_run_error(*, run_id: str | None, error: str | None) -> None:
    if not run_id:
        return
    _repo().finalize_if_running(run_id=run_id, status="error", error=error)
