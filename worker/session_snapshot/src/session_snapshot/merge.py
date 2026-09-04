from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def _is_valid_storage_snapshot(storage: dict[str, Any]) -> bool:
    if not isinstance(storage, dict):
        return False
    origin = storage.get("origin")
    if not isinstance(origin, str) or not origin.strip():
        return False
    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return isinstance(storage.get("localStorage", {}), dict) and isinstance(
        storage.get("sessionStorage", {}),
        dict,
    )


def _is_persistable_tab_url(tab_url: str | None) -> bool:
    if not isinstance(tab_url, str) or not tab_url.strip():
        return False
    parsed = urlparse(tab_url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def merge_session_payload(
    base_payload: dict[str, Any],
    *,
    cookies: list[dict[str, Any]],
    storage: dict[str, Any],
    tab_url: str | None,
    account_timezone: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = deepcopy(base_payload if isinstance(base_payload, dict) else {})
    if cookies:
        payload["cookies"] = cookies
    if _is_valid_storage_snapshot(storage):
        payload["storage"] = storage

    tab = payload.get("tab") if isinstance(payload.get("tab"), dict) else {}
    if _is_persistable_tab_url(tab_url):
        tab["url"] = tab_url
    payload["tab"] = tab

    browser = payload.get("browser") if isinstance(payload.get("browser"), dict) else {}
    fingerprint_timezone = str(account_timezone or "").strip()
    if fingerprint_timezone:
        browser["timeZone"] = fingerprint_timezone
    payload["browser"] = browser

    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    diagnostics["captured_at"] = datetime.now(timezone.utc).isoformat()
    diagnostics["source"] = "server_browser"
    payload["diagnostics"] = diagnostics
    return payload


def merge_snapshot(
    base: dict[str, Any],
    *,
    cookies: list[dict[str, Any]],
    storage: dict[str, Any],
    tab_url: str | None,
    browser_timezone: str | None = None,
) -> dict[str, Any]:
    return merge_session_payload(
        base,
        cookies=cookies,
        storage=storage,
        tab_url=tab_url,
        account_timezone=browser_timezone,
    )
