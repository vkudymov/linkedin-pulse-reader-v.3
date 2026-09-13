from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list, expect_single

from .models import JobSearchCreate, JobSearchRow


class JobSearchRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def list_by_user(self, *, user_id: str) -> list[JobSearchRow]:
        resp = (
            self._client.table("job_searches")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return expect_list(resp)  # type: ignore[return-value]

    def get_by_id(self, *, job_search_id: str) -> JobSearchRow | None:
        resp = (
            self._client.table("job_searches")
            .select("*")
            .eq("id", job_search_id)
            .maybe_single()
            .execute()
        )
        data = getattr(resp, "data", None)
        return data if isinstance(data, dict) else None  # type: ignore[return-value]

    def create(
        self,
        *,
        user_id: str,
        title: str,
        search_query: str,
        location: str | None,
        filter_prompt: str,
        status: str = "active",
    ) -> JobSearchRow:
        payload: JobSearchCreate = {
            "user_id": user_id,
            "title": title,
            "search_query": search_query,
            "location": location,
            "filter_prompt": filter_prompt,
            "status": status,
            "last_run_at": None,
        }
        resp = self._client.table("job_searches").insert(payload).execute()
        return expect_single(resp)  # type: ignore[return-value]

    def update(
        self,
        *,
        job_search_id: str,
        title: str | None = None,
        search_query: str | None = None,
        location: str | None = None,
        filter_prompt: str | None = None,
        status: str | None = None,
        last_run_at: str | None = None,
    ) -> JobSearchRow:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {"updated_at": now}
        if title is not None:
            payload["title"] = title
        if search_query is not None:
            payload["search_query"] = search_query
        if location is not None:
            payload["location"] = location
        if filter_prompt is not None:
            payload["filter_prompt"] = filter_prompt
        if status is not None:
            payload["status"] = status
        if last_run_at is not None:
            payload["last_run_at"] = last_run_at

        resp = (
            self._client.table("job_searches")
            .update(payload)
            .eq("id", job_search_id)
            .select("*")
            .execute()
        )
        return expect_single(resp)  # type: ignore[return-value]

    def delete(self, *, job_search_id: str) -> None:
        self._client.table("job_searches").delete().eq("id", job_search_id).execute()

