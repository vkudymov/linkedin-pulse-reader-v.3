from __future__ import annotations

from typing import Any


def persist_cookies(
    *,
    user_id: str,
    cookies: list[dict[str, Any]],
    label: str | None,
) -> str:
    """
    Create or update `linkedin_accounts` row for a given user, and persist cookies_json.

    Returns linkedin_account_id.
    """
    from storage import PulseStorage  # type: ignore[import-not-found]

    storage = PulseStorage()
    accounts = storage.linkedin_accounts
    rows = accounts.list_by_user(user_id=user_id)

    chosen: dict[str, Any] | None = None
    if label:
        chosen = next((a for a in rows if a.get("label") == label), None)
    if chosen is None:
        chosen = rows[0] if rows else None

    if chosen is None:
        created = accounts.create(user_id=user_id, cookies_json=cookies, label=label)
        return created["id"]

    updated = accounts.update_cookies(account_id=chosen["id"], cookies_json=cookies)
    return updated["id"]

