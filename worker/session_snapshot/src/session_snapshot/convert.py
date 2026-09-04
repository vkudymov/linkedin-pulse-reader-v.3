from __future__ import annotations

from typing import Any


def chrome_cookie_to_playwright(cookie: dict[str, Any]) -> dict[str, Any]:
    domain = cookie.get("domain")
    domain_without_dot = (domain or "").lstrip(".")
    path = cookie.get("path") or "/"
    scheme = "https" if cookie.get("secure", False) else "http"
    cookie_url = f"{scheme}://{domain_without_dot}{path}" if domain_without_dot else None

    same_site_map = {
        "no_restriction": "None",
        "lax": "Lax",
        "strict": "Strict",
        "unspecified": None,
        "None": "None",
        "Lax": "Lax",
        "Strict": "Strict",
    }
    normalized_same_site = same_site_map.get(cookie.get("sameSite") or "")

    playwright_cookie: dict[str, Any] = {
        "name": cookie["name"],
        "value": cookie["value"],
        "secure": bool(cookie.get("secure", False)),
        "httpOnly": bool(cookie.get("httpOnly", False)),
    }
    if normalized_same_site:
        playwright_cookie["sameSite"] = normalized_same_site
    expires = cookie.get("expirationDate")
    if isinstance(expires, (int, float)) and expires > 0:
        playwright_cookie["expires"] = int(expires)

    if domain:
        playwright_cookie["domain"] = domain
        playwright_cookie["path"] = path
    elif cookie_url:
        playwright_cookie["url"] = cookie_url
    return playwright_cookie


def playwright_cookies_to_extension(cookies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "").strip()
        value = str(cookie.get("value") or "")
        if not name:
            continue
        exported_cookie: dict[str, Any] = {
            "name": name,
            "value": value,
            "domain": cookie.get("domain"),
            "path": cookie.get("path") or "/",
            "secure": bool(cookie.get("secure", False)),
            "httpOnly": bool(cookie.get("httpOnly", False)),
            "sameSite": cookie.get("sameSite"),
        }
        expires = cookie.get("expires")
        if isinstance(expires, (int, float)) and expires > 0:
            exported_cookie["expirationDate"] = float(expires)
        exported.append(exported_cookie)
    return exported


def to_playwright_cookies(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        chrome_cookie_to_playwright(cookie)
        for cookie in raw
        if isinstance(cookie, dict) and "name" in cookie and "value" in cookie
    ]


def from_playwright_cookies(pw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return playwright_cookies_to_extension(pw)


def playwright_cookies_for_context(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return to_playwright_cookies(raw)
