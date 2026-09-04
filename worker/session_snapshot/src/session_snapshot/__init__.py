from __future__ import annotations

from .adapter import is_snapshot_payload, load_snapshot, playwright_list_to_snapshot
from .convert import (
    chrome_cookie_to_playwright,
    from_playwright_cookies,
    playwright_cookies_for_context,
    playwright_cookies_to_extension,
    to_playwright_cookies,
)
from .linkedin import (
    AUTH_COOKIE_NAME,
    DEFAULT_ORIGIN,
    LOGOUT_URL_HINTS,
    TARGET_HOST_SUFFIX,
    has_auth_cookie,
    is_logged_out,
    should_save_back,
)
from .merge import merge_session_payload, merge_snapshot
from .restore import SessionLoggedOutError, export_session, playwright_context_options, restore_session
from .storage import apply_storage_snapshot, capture_storage_from_page, seed_origin_storage

__all__ = [
    "AUTH_COOKIE_NAME",
    "DEFAULT_ORIGIN",
    "LOGOUT_URL_HINTS",
    "TARGET_HOST_SUFFIX",
    "SessionLoggedOutError",
    "apply_storage_snapshot",
    "capture_storage_from_page",
    "chrome_cookie_to_playwright",
    "export_session",
    "from_playwright_cookies",
    "has_auth_cookie",
    "is_logged_out",
    "is_snapshot_payload",
    "load_snapshot",
    "merge_session_payload",
    "merge_snapshot",
    "playwright_context_options",
    "playwright_cookies_for_context",
    "playwright_cookies_to_extension",
    "playwright_list_to_snapshot",
    "restore_session",
    "seed_origin_storage",
    "should_save_back",
    "to_playwright_cookies",
]
