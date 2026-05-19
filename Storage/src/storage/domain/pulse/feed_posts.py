from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping

from storage.core.response import expect_list
from storage.errors import StorageResponseError

from .models import FeedPostUpsert


class FeedPostRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def upsert_posts(
        self,
        *,
        linkedin_account_id: str,
        posts: list[dict[str, Any]],
    ) -> int:
        rows: list[FeedPostUpsert] = [
            _to_upsert_row(linkedin_account_id=linkedin_account_id, post=post)
            for post in posts
            if isinstance(post, Mapping)
        ]

        if not rows:
            return 0

        resp = (
            self._client.table("feed_posts")
            .upsert(rows, on_conflict="linkedin_account_id,source_key")
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise StorageResponseError("Expected list response from Supabase upsert.")
        return len(data)

    def update_analysis(
        self,
        *,
        linkedin_account_id: str,
        source_key: str,
        is_relevant: bool | None,
        comment_text: str | None,
        analysis_error: str | None,
        analysis_payload: dict[str, Any] | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload: dict[str, Any] = {
            "is_relevant": is_relevant,
            "comment_text": comment_text,
            "analysis_error": analysis_error,
            "analysis_payload": analysis_payload,
            "analyzed_at": now,
        }
        (
            self._client.table("feed_posts")
            .update(payload)
            .eq("linkedin_account_id", linkedin_account_id)
            .eq("source_key", source_key)
            .execute()
        )

    def list_for_account(
        self,
        *,
        linkedin_account_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        resp = (
            self._client.table("feed_posts")
            .select("*")
            .eq("linkedin_account_id", linkedin_account_id)
            .order("fetched_at", desc=True)
            .limit(limit)
            .execute()
        )
        return expect_list(resp)


def compute_source_key(post: Mapping[str, Any]) -> str:
    urn = post.get("urn")
    if isinstance(urn, str) and (s := urn.strip()):
        return s

    post_url = post.get("post_url")
    if isinstance(post_url, str) and (s := post_url.strip()):
        return s

    pid = post.get("id")
    if isinstance(pid, str) and (s := pid.strip()):
        return f"id:{s}"

    author = post.get("author")
    author_name = author.get("name") if isinstance(author, Mapping) else None
    published_at_text = post.get("published_at_text")
    content = post.get("content") or post.get("text") or ""
    base = f"{author_name or ''}|{published_at_text or ''}|{str(content)[:200]}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    return f"fallback:{digest}"


def _to_upsert_row(*, linkedin_account_id: str, post: Mapping[str, Any]) -> FeedPostUpsert:
    source_key = compute_source_key(post)

    post_url_val = post.get("post_url")
    post_url = post_url_val.strip() if isinstance(post_url_val, str) else ""

    urn = post.get("urn")
    urn_val = urn.strip() if isinstance(urn, str) else None

    media_urls_val = post.get("media_urls")
    media_urls = (
        [u for u in media_urls_val if isinstance(u, str)]
        if isinstance(media_urls_val, list)
        else []
    )

    raw_extra_val = post.get("extra")
    raw_extra = raw_extra_val if isinstance(raw_extra_val, dict) else None

    author_val = post.get("author")
    author_json = author_val if isinstance(author_val, dict) else None

    row: FeedPostUpsert = {
        "linkedin_account_id": linkedin_account_id,
        "source_key": source_key,
        "post_url": post_url,
        "urn": urn_val,
        "author_json": author_json,
        "content": post.get("content") if isinstance(post.get("content"), str) else None,
        "published_at_text": (
            post.get("published_at_text") if isinstance(post.get("published_at_text"), str) else None
        ),
        "reactions_count": post.get("reactions_count") if isinstance(post.get("reactions_count"), int) else None,
        "comments_count": post.get("comments_count") if isinstance(post.get("comments_count"), int) else None,
        "media_urls": media_urls,
        "raw_extra": raw_extra,
    }
    return row

