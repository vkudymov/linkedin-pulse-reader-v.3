from __future__ import annotations

from typing import Any


def persist_cookies(
    *,
    user_id: str,
    cookies: list[dict[str, Any]],
    label: str | None,
    session_snapshot: dict[str, Any] | None = None,
) -> str:
    """
    Create or update `linkedin_accounts` for a user.

    Prefer `persist_snapshot` after UI login. This wrapper keeps cookies_json in sync.
    """
    snapshot = session_snapshot
    if snapshot is None:
        try:
            from session_snapshot import playwright_list_to_snapshot

            snapshot = playwright_list_to_snapshot(cookies)
        except ImportError:
            snapshot = None
    return persist_snapshot(user_id=user_id, snapshot=snapshot, cookies=cookies, label=label)


def persist_snapshot(
    *,
    user_id: str,
    snapshot: dict[str, Any] | None,
    label: str | None,
    cookies: list[dict[str, Any]] | None = None,
) -> str:
    from storage import PulseStorage, pick_linkedin_account_row  # type: ignore[import-not-found]

    storage = PulseStorage()
    accounts = storage.linkedin_accounts
    rows = accounts.list_by_user(user_id=user_id)

    chosen = pick_linkedin_account_row(
        rows,
        label=label,
        create_new_on_label_miss=False,
    )

    cookie_list: list[dict[str, Any]] = []
    if isinstance(snapshot, dict):
        raw = snapshot.get("cookies")
        if isinstance(raw, list):
            cookie_list = raw
    if not cookie_list and cookies is not None:
        cookie_list = cookies

    if chosen is None:
        created = accounts.create(
            user_id=user_id,
            cookies_json=cookie_list,
            label=label,
            session_snapshot=snapshot,
        )
        return created["id"]

    if snapshot is not None:
        updated = accounts.update_session(account_id=chosen["id"], session_snapshot=snapshot)
        return updated["id"]

    updated = accounts.update_cookies(account_id=chosen["id"], cookies_json=cookie_list)
    return updated["id"]
