from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from storage.core.response import expect_single

RunStatus = Literal["running", "done", "error", "lost"]
RunKind = Literal["post", "job"]


class SearchRunRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def create_running(
        self,
        *,
        user_id: str,
        kind: RunKind,
        search_title: str,
        limit_count: int,
        search_id: str | None = None,
        account_label: str | None = None,
        search_query: str | None = None,
        location: str | None = None,
        linkedin_filters: dict[str, Any] | None = None,
        search_prompt: str | None = None,
        comment_prompt: str | None = None,
        filter_prompt: str | None = None,
        session_id: str | None = None,
        initiated_by: str = "user",
        admin_actor_id: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {
            "user_id": user_id,
            "kind": kind,
            "search_title": search_title,
            "limit_count": limit_count,
            "account_label": account_label,
            "search_query": search_query,
            "location": location,
            "linkedin_filters": linkedin_filters,
            "search_prompt": search_prompt,
            "comment_prompt": comment_prompt,
            "filter_prompt": filter_prompt,
            "status": "running",
            "started_at": now,
            "session_id": session_id,
            "initiated_by": initiated_by,
            "admin_actor_id": admin_actor_id,
            "updated_at": now,
        }
        if search_id:
            payload["search_id"] = search_id
        resp = self._client.table("search_runs").insert(payload).execute()
        return expect_single(resp)  # type: ignore[return-value]

    def set_session_id(self, *, run_id: str, session_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        self._client.table("search_runs").update({"session_id": session_id, "updated_at": now}).eq(
            "id", run_id
        ).execute()

    def finalize(
        self,
        *,
        run_id: str,
        status: RunStatus,
        fetched_count: int | None = None,
        analyzed_count: int | None = None,
        matched_count: int | None = None,
        error: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {
            "status": status,
            "finished_at": now,
            "updated_at": now,
        }
        if fetched_count is not None:
            payload["fetched_count"] = fetched_count
        if analyzed_count is not None:
            payload["analyzed_count"] = analyzed_count
        if matched_count is not None:
            payload["matched_count"] = matched_count
        if error is not None:
            payload["error"] = (error[:240] or None) if error else None
        self._client.table("search_runs").update(payload).eq("id", run_id).execute()

    def get_by_session_id(self, *, user_id: str, session_id: str) -> dict[str, Any] | None:
        resp = (
            self._client.table("search_runs")
            .select("id,user_id,session_id,status,error,kind")
            .eq("user_id", user_id)
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        data = getattr(resp, "data", None)
        if isinstance(data, list):
            row = next((item for item in data if isinstance(item, dict)), None)
            return row
        if isinstance(data, dict):
            return data
        return None

    def mark_lost_if_running(self, *, run_id: str, error: str) -> dict[str, Any] | None:
        now = datetime.now(UTC).isoformat()
        resp = (
            self._client.table("search_runs")
            .update(
                {
                    "status": "lost",
                    "error": error[:240] if error else None,
                    "finished_at": now,
                    "updated_at": now,
                }
            )
            .eq("id", run_id)
            .eq("status", "running")
            .select("id,user_id,session_id,status,error,kind")
            .execute()
        )
        data = getattr(resp, "data", None)
        if isinstance(data, list):
            row = next((item for item in data if isinstance(item, dict)), None)
            return row
        if isinstance(data, dict):
            return data
        return None

    def finalize_if_running(
        self,
        *,
        run_id: str,
        status: RunStatus,
        error: str | None = None,
    ) -> None:
        resp = (
            self._client.table("search_runs")
            .select("id,status")
            .eq("id", run_id)
            .maybe_single()
            .execute()
        )
        row = getattr(resp, "data", None)
        if not isinstance(row, dict) or row.get("status") != "running":
            return
        self.finalize(run_id=run_id, status=status, error=error)

    def list_for_admin(
        self,
        *,
        user_id: str | None = None,
        kind: RunKind | None = None,
        search_id: str | None = None,
        status: RunStatus | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        order: Literal["asc", "desc"] = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        q = self._client.table("search_runs").select("*", count="exact")
        if user_id:
            q = q.eq("user_id", user_id)
        if kind:
            q = q.eq("kind", kind)
        if search_id:
            q = q.eq("search_id", search_id)
        if status:
            q = q.eq("status", status)
        if date_from:
            q = q.gte("started_at", date_from)
        if date_to:
            q = q.lte("started_at", date_to)

        q = q.order("started_at", desc=order == "desc").range(offset, offset + limit - 1)
        resp = q.execute()
        data = getattr(resp, "data", None)
        rows = [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
        total_raw = getattr(resp, "count", None)
        total = int(total_raw) if isinstance(total_raw, int) else len(rows)
        return rows, total
