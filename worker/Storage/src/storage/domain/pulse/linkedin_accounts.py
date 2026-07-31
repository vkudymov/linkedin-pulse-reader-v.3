from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from storage.core.response import expect_list, expect_single

from .models import LinkedInAccountCreate, LinkedInAccountRow


class LinkedInAccountRepository:
    """One row per LinkedIn session; cookies_json is the browser session state."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def list_by_user(self, *, user_id: str) -> list[LinkedInAccountRow]:
        resp = (
            self._client.table("linkedin_accounts")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return expect_list(resp)  # type: ignore[return-value]

    def create(
        self,
        *,
        user_id: str,
        cookies_json: list[dict[str, Any]],
        label: str | None = None,
        li_profile_url: str | None = None,
    ) -> LinkedInAccountRow:
        now = datetime.now(timezone.utc).isoformat()
        payload: LinkedInAccountCreate = {
            "user_id": user_id,
            "cookies_json": cookies_json,
            "cookies_updated_at": now,
        }
        if label is not None:
            payload["label"] = label
        if li_profile_url is not None:
            payload["li_profile_url"] = li_profile_url

        return expect_single(self._client.table("linkedin_accounts").insert(payload).execute())  # type: ignore[return-value]

    def update_cookies(
        self,
        *,
        account_id: str,
        cookies_json: list[dict[str, Any]],
    ) -> LinkedInAccountRow:
        now = datetime.now(timezone.utc).isoformat()
        resp = (
            self._client.table("linkedin_accounts")
            .update({"cookies_json": cookies_json, "cookies_updated_at": now, "updated_at": now})
            .eq("id", account_id)
            .select("*")
            .execute()
        )
        return expect_single(resp)  # type: ignore[return-value]

