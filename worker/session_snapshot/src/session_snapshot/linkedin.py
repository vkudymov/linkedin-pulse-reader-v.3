from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

TARGET_HOST_SUFFIX = "linkedin.com"
AUTH_COOKIE_NAME = "li_at"
DEFAULT_ORIGIN = "https://www.linkedin.com"
LOGOUT_URL_HINTS = ["/login", "/checkpoint", "/authwall", "/uas/"]


def has_auth_cookie(cookies: list[dict[str, Any]], name: str = AUTH_COOKIE_NAME) -> bool:
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        if str(cookie.get("name") or "") == name and str(cookie.get("value") or "") != "":
            return True
    return False


def is_logged_out(url: str, hints: list[str] | None = None) -> bool:
    lowered = (url or "").lower()
    markers = hints if hints is not None else LOGOUT_URL_HINTS
    parsed = urlparse(lowered)
    haystack = f"{parsed.path}?{parsed.query}"
    return any(marker.lower() in haystack or marker.lower() in lowered for marker in markers)


def should_save_back(url: str) -> bool:
    return not is_logged_out(url)
