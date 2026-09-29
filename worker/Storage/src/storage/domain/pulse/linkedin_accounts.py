from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list, expect_single
from storage.session_crypto import decrypt_json, encrypt_json

from .models import LinkedInAccountRow


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
        return [_open_account_row(row) for row in expect_list(resp)]  # type: ignore[return-value]

    def create(
        self,
        *,
        user_id: str,
        session_snapshot: dict[str, Any],
        label: str | None = None,
        li_profile_url: str | None = None,
    ) -> LinkedInAccountRow:
        now = datetime.now(UTC).isoformat()
        sealed_cookies, sealed_snapshot = _seal_session(session_snapshot)
        payload: dict[str, Any] = {
            "user_id": user_id,
            "cookies_json": sealed_cookies,
            "cookies_updated_at": now,
            "session_snapshot": sealed_snapshot,
        }
        if label is not None:
            payload["label"] = label
        if li_profile_url is not None:
            payload["li_profile_url"] = li_profile_url

        inserted = expect_single(self._client.table("linkedin_accounts").insert(payload).execute())
        return _open_account_row(inserted)

    def update_session(
        self,
        *,
        account_id: str,
        session_snapshot: dict[str, Any],
    ) -> LinkedInAccountRow:
        now = datetime.now(UTC).isoformat()
        sealed_cookies, sealed_snapshot = _seal_session(session_snapshot)
        resp = (
            self._client.table("linkedin_accounts")
            .update(
                {
                    "session_snapshot": sealed_snapshot,
                    "cookies_json": sealed_cookies,
                    "cookies_updated_at": now,
                    "updated_at": now,
                }
            )
            .eq("id", account_id)
            .select("*")
            .execute()
        )
        return _open_account_row(expect_single(resp))


def _seal_session(snapshot: dict[str, Any]) -> tuple[str, str]:
    cookies = _playwright_cookies_from_snapshot(snapshot)
    return encrypt_json(cookies), encrypt_json(snapshot)


def _open_account_row(row: dict[str, Any]) -> LinkedInAccountRow:
    opened = dict(row)
    opened["cookies_json"] = decrypt_json(opened.get("cookies_json"))
    if opened.get("session_snapshot") is not None:
        opened["session_snapshot"] = decrypt_json(opened.get("session_snapshot"))
    return opened  # type: ignore[return-value]


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
