from __future__ import annotations

from typing import Any

from storage.errors import StorageResponseError

from .models import JobAnalysisUpsert


class JobAnalysisRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def upsert_analyses(
        self,
        *,
        analyses: list[JobAnalysisUpsert],
    ) -> int:
        if not analyses:
            return 0
        resp = (
            self._client.table("job_analyses")
            .upsert(analyses, on_conflict="job_search_id,job_id")
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise StorageResponseError("Expected list response from Supabase upsert.")
        return len(data)

