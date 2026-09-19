from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list, expect_single

from .models import PostSearchCreate, PostSearchRow


class PostSearchRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def list_by_user(self, *, user_id: str) -> list[PostSearchRow]:
        resp = (
            self._client.table("post_searches")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return expect_list(resp)  # type: ignore[return-value]

    def get_by_id(self, *, post_search_id: str) -> PostSearchRow | None:
        resp = (
            self._client.table("post_searches")
            .select("*")
            .eq("id", post_search_id)
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
        search_prompt: str,
        comment_prompt: str | None,
        account_label: str | None = None,
        status: str = "active",
    ) -> PostSearchRow:
        payload: PostSearchCreate = {
            "user_id": user_id,
            "title": title,
            "search_prompt": search_prompt,
            "comment_prompt": comment_prompt,
            "account_label": account_label,
            "status": status,
            "last_run_at": None,
        }
        resp = self._client.table("post_searches").insert(payload).execute()
        return expect_single(resp)  # type: ignore[return-value]

    def update(
        self,
        *,
        post_search_id: str,
        title: str | None = None,
        search_prompt: str | None = None,
        comment_prompt: str | None = None,
        account_label: str | None = None,
        status: str | None = None,
        last_run_at: str | None = None,
    ) -> PostSearchRow:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {"updated_at": now}
        if title is not None:
            payload["title"] = title
        if search_prompt is not None:
            payload["search_prompt"] = search_prompt
        if comment_prompt is not None:
            payload["comment_prompt"] = comment_prompt
        if account_label is not None:
            payload["account_label"] = account_label
        if status is not None:
            payload["status"] = status
        if last_run_at is not None:
            payload["last_run_at"] = last_run_at
        resp = (
            self._client.table("post_searches")
            .update(payload)
            .eq("id", post_search_id)
            .select("*")
            .execute()
        )
        return expect_single(resp)  # type: ignore[return-value]

    def delete(self, *, post_search_id: str) -> None:
        self._client.table("post_searches").delete().eq("id", post_search_id).execute()

