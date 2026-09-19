from __future__ import annotations

from typing import Any

from storage.errors import StorageResponseError

from .models import PostAnalysisUpsert


class PostAnalysisRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def upsert_analyses(self, *, analyses: list[PostAnalysisUpsert]) -> int:
        if not analyses:
            return 0
        resp = (
            self._client.table("post_analyses")
            .upsert(analyses, on_conflict="post_search_id,feed_post_id")
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise StorageResponseError("Expected list response from Supabase upsert.")
        return len(data)

    def list_for_search(self, *, post_search_id: str, limit: int = 200) -> list[dict[str, Any]]:
        resp = (
            self._client.table("post_analyses")
            .select("*")
            .eq("post_search_id", post_search_id)
            .order("analyzed_at", desc=True)
            .limit(limit)
            .execute()
        )
        data = getattr(resp, "data", None)
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

