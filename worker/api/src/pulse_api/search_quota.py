from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, NoReturn, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")

_BLOCKED = 403
_FAILED = 500


class SearchQuotaError(Exception):
    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def increment_post_search_run_count(*, client: Any, user_id: str) -> int:
    """Atomically increment ``post_search_run_count`` via SQL RPC."""
    try:
        resp = client.rpc(
            "increment_post_search_run_count",
            {"p_user_id": user_id},
        ).execute()
    except Exception as exc:
        text = str(exc)
        log.exception("post_search_run_count increment failed for user_id=%s", user_id)
        if "user_blocked" in text:
            raise SearchQuotaError("Пользователь заблокирован.", _BLOCKED) from exc
        raise SearchQuotaError("Failed to update search run counter.", _FAILED) from exc

    data = getattr(resp, "data", None)
    if isinstance(data, bool) or data is None:
        raise SearchQuotaError("Failed to update search run counter.", _FAILED)
    if isinstance(data, int):
        return data
    if isinstance(data, str) and data.isdigit():
        return int(data)
    raise SearchQuotaError("Failed to update search run counter.", _FAILED)


def charge_post_search_quota_after_start(
    *,
    client: Any,
    user_id: str,
    start: Callable[[], T],
) -> T:
    """
    Run ``start`` first. Increment the quota only when it returns.

    A failed start leaves the counter unchanged. An increment failure is raised
    and is not ignored.
    """
    started = start()
    increment_post_search_run_count(client=client, user_id=user_id)
    return started


def raise_for_quota(exc: SearchQuotaError) -> NoReturn:
    from fastapi import HTTPException

    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
