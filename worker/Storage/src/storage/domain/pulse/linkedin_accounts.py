from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from storage.core.response import expect_list, expect_single

from .models import LinkedInAccountCreate, LinkedInAccountRow


def pick_linkedin_account_row(
    rows: list[LinkedInAccountRow],
    *,
    label: str | None,
    create_new_on_label_miss: bool,
) -> LinkedInAccountRow | None:
    if label:
        matched = next((row for row in rows if row.get("label") == label), None)
        if matched is not None:
            return matched
        if create_new_on_label_miss:
            return None
    return rows[0] if rows else None


class LinkedInAccountRepository:
    """One row per LinkedIn session; session_snapshot is the browser session state."""

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
        session_snapshot: dict[str, Any],
        label: str | None = None,
        li_profile_url: str | None = None,
    ) -> LinkedInAccountRow:
        now = datetime.now(timezone.utc).isoformat()
        payload: LinkedInAccountCreate = {
            "user_id": user_id,
            "cookies_json": _playwright_cookies_from_snapshot(session_snapshot),
            "cookies_updated_at": now,
            "session_snapshot": session_snapshot,
        }
        if label is not None:
            payload["label"] = label
        if li_profile_url is not None:
            payload["li_profile_url"] = li_profile_url

        return expect_single(self._client.table("linkedin_accounts").insert(payload).execute())  # type: ignore[return-value]

    def update_session(
        self,
        *,
        account_id: str,
        session_snapshot: dict[str, Any],
    ) -> LinkedInAccountRow:
        now = datetime.now(timezone.utc).isoformat()
        resp = (
            self._client.table("linkedin_accounts")
            .update(
                {
                    "session_snapshot": session_snapshot,
                    "cookies_json": _playwright_cookies_from_snapshot(session_snapshot),
                    "cookies_updated_at": now,
                    "updated_at": now,
                }
            )
            .eq("id", account_id)
            .select("*")
            .execute()
        )
        return expect_single(resp)  # type: ignore[return-value]


def _playwright_cookies_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Mirror snapshot cookies into cookies_json (NOT NULL legacy column)."""
    cookies = snapshot.get("cookies") if isinstance(snapshot, dict) else None
    if not isinstance(cookies, list):
        return []
    raw = [c for c in cookies if isinstance(c, dict)]
    try:
        from session_snapshot import to_playwright_cookies
    except ImportError:
        return raw
    return to_playwright_cookies(raw) or raw
