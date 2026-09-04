from __future__ import annotations

from typing import Any


def persist_snapshot(
    *,
    user_id: str,
    snapshot: dict[str, Any],
    label: str | None,
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

    if chosen is None:
        created = accounts.create(
            user_id=user_id,
            session_snapshot=snapshot,
            label=label,
        )
        return created["id"]

    updated = accounts.update_session(account_id=chosen["id"], session_snapshot=snapshot)
    return updated["id"]
