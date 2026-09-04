from __future__ import annotations

import logging
from typing import Any

from .convert import from_playwright_cookies, to_playwright_cookies
from .linkedin import has_auth_cookie, is_logged_out
from .merge import merge_snapshot
from .storage import capture_storage_from_page, seed_origin_storage

_log = logging.getLogger(__name__)


class SessionLoggedOutError(RuntimeError):
    """Raised when export is attempted on a login-wall URL. Pulse maps this to LoginRequiredError."""


def restore_session(context: Any, page: Any, snapshot: dict[str, Any]) -> None:
    raw_cookies = snapshot.get("cookies") if isinstance(snapshot, dict) else None
    raw_list = raw_cookies if isinstance(raw_cookies, list) else []
    cookies = to_playwright_cookies(raw_list)
    _log.info(
        "session_snapshot: user cookies selected (count=%s, li_at=%s)",
        len(cookies),
        "yes" if has_auth_cookie(raw_list) else "no",
    )
    if cookies:
        context.add_cookies(cookies)
    storage = snapshot.get("storage") if isinstance(snapshot, dict) else None
    seeded = False
    if isinstance(storage, dict):
        seed_origin_storage(page, storage)
        seeded = True
    _log.info(
        "session_snapshot: restore_session applied cookies to Playwright — OK (storage_seeded=%s)",
        seeded,
    )


def export_session(
    context: Any,
    page: Any,
    base_snapshot: dict[str, Any],
    *,
    browser_timezone: str | None = None,
) -> dict[str, Any]:
    tab_url = ""
    try:
        tab_url = str(page.url or "")
    except Exception:
        tab_url = ""
    if is_logged_out(tab_url):
        raise SessionLoggedOutError("LinkedIn session is on a login-wall URL; do not save-back.")
    pw_cookies = context.cookies() if context is not None else []
    if not isinstance(pw_cookies, list):
        pw_cookies = []
    storage = capture_storage_from_page(page)
    merged = merge_snapshot(
        base_snapshot if isinstance(base_snapshot, dict) else {},
        cookies=from_playwright_cookies(pw_cookies),
        storage=storage,
        tab_url=tab_url,
        browser_timezone=browser_timezone,
    )
    merged_cookies = merged.get("cookies") if isinstance(merged, dict) else []
    _log.info(
        "session_snapshot: export_session saved snapshot — OK (count=%s)",
        len(merged_cookies) if isinstance(merged_cookies, list) else 0,
    )
    return merged


def playwright_context_options(snapshot: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    options: dict[str, Any] = {}
    browser = snapshot.get("browser") if isinstance(snapshot.get("browser"), dict) else {}
    viewport = snapshot.get("viewport") if isinstance(snapshot.get("viewport"), dict) else {}
    user_agent = browser.get("userAgent")
    if isinstance(user_agent, str) and user_agent.strip():
        options["user_agent"] = user_agent.strip()
    language = browser.get("language")
    if isinstance(language, str) and language.strip():
        options["locale"] = language.strip()
    width = viewport.get("innerWidth")
    height = viewport.get("innerHeight")
    if isinstance(width, (int, float)) and isinstance(height, (int, float)) and width > 0 and height > 0:
        options["viewport"] = {"width": int(width), "height": int(height)}
    return options
