from __future__ import annotations

from typing import Any

from .convert import from_playwright_cookies
from .linkedin import DEFAULT_ORIGIN


def is_snapshot_payload(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("cookies"), list)


def playwright_list_to_snapshot(cookies: list[dict[str, Any]]) -> dict[str, Any]:
    chrome_cookies = from_playwright_cookies(cookies if isinstance(cookies, list) else [])
    return {
        "createdAt": "",
        "cookies": chrome_cookies,
        "storage": {
            "origin": DEFAULT_ORIGIN,
            "localStorage": {},
            "sessionStorage": {},
        },
        "browser": {},
        "viewport": {},
        "tab": {"url": "", "title": ""},
        "diagnostics": {"cookieCount": len(chrome_cookies), "captured_at": "", "source": "legacy_playwright_list"},
    }


def empty_snapshot() -> dict[str, Any]:
    return {
        "createdAt": "",
        "cookies": [],
        "storage": {
            "origin": DEFAULT_ORIGIN,
            "localStorage": {},
            "sessionStorage": {},
        },
        "browser": {},
        "viewport": {},
        "tab": {"url": "", "title": ""},
        "diagnostics": {"cookieCount": 0, "captured_at": "", "source": "empty"},
    }


def load_snapshot(account_row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(account_row, dict):
        return empty_snapshot()

    nested = account_row.get("session_snapshot")
    if is_snapshot_payload(nested):
        return nested

    cookies_json = account_row.get("cookies_json")
    if is_snapshot_payload(cookies_json):
        return cookies_json
    if isinstance(cookies_json, list) and all(
        isinstance(item, dict) for item in cookies_json
    ):
        return playwright_list_to_snapshot(cookies_json)

    if is_snapshot_payload(account_row):
        return account_row

    return empty_snapshot()
