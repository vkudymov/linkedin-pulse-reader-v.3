from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list
from storage.errors import StorageResponseError

from .models import JobRow, JobUpsert


class JobRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def upsert_jobs(
        self,
        *,
        user_id: str,
        linkedin_account_id: str,
        jobs: list[dict[str, Any]],
    ) -> list[JobRow]:
        now = datetime.now(UTC).isoformat()
        rows: list[JobUpsert] = []
        for j in jobs:
            if not isinstance(j, Mapping):
                continue
            source_key = j.get("source_key")
            job_url = j.get("job_url")
            title = j.get("title")
            if not isinstance(source_key, str) or not source_key.strip():
                continue
            if not isinstance(job_url, str) or not job_url.strip():
                continue
            if not isinstance(title, str) or not title.strip():
                continue
            rows.append(
                {
                    "user_id": user_id,
                    "linkedin_account_id": linkedin_account_id,
                    "source_key": source_key.strip(),
                    "linkedin_job_id": j.get("linkedin_job_id")
                    if isinstance(j.get("linkedin_job_id"), str)
                    else None,
                    "job_url": job_url.strip(),
                    "title": title.strip(),
                    "company": j.get("company") if isinstance(j.get("company"), str) else None,
                    "location": j.get("location") if isinstance(j.get("location"), str) else None,
                    "description": j.get("description")
                    if isinstance(j.get("description"), str)
                    else None,
                    "raw_extra": (
                        j.get("raw_extra") if isinstance(j.get("raw_extra"), dict) else None
                    ),
                    "fetched_at": now,
                    "updated_at": now,
                },
            )

        if not rows:
            return []

        resp = (
            self._client.table("jobs")
            .upsert(rows, on_conflict="user_id,source_key")
            .select("*")
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise StorageResponseError("Expected list response from Supabase upsert.")
        return data  # type: ignore[return-value]

    def list_for_user(
        self,
        *,
        user_id: str,
        limit: int = 100,
    ) -> list[JobRow]:
        resp = (
            self._client.table("jobs")
            .select("*")
            .eq("user_id", user_id)
            .order("fetched_at", desc=True)
            .limit(limit)
            .execute()
        )
        return expect_list(resp)  # type: ignore[return-value]

