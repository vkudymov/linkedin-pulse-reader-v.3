from __future__ import annotations

"""
RU: Cookies boundary (внешнее состояние).
    Библиотека принимает cookies, применяет их к контексту и может извлечь обновлённые cookies обратно.
    Хранение и управление пользователями остаётся во внешнем приложении.

EN: Cookies boundary (external state).
    The library accepts cookies, applies them to the browser context, and can extract refreshed cookies.
    Persistence and user management remain in the calling application.
"""

from typing import Any, Mapping, Sequence, TypeAlias

from playwright.sync_api import BrowserContext

from ..exceptions import CookieFormatError

Cookie: TypeAlias = Mapping[str, Any]
Cookies: TypeAlias = Sequence[Cookie]


def _validate_cookie(cookie: Cookie) -> None:
    name = cookie.get("name")
    value = cookie.get("value")
    if not isinstance(name, str) or not name:
        raise CookieFormatError("Cookie missing required string field: name")
    if not isinstance(value, str):
        raise CookieFormatError("Cookie missing required string field: value")

    has_domain = isinstance(cookie.get("domain"), str) and bool(cookie.get("domain"))
    has_url = isinstance(cookie.get("url"), str) and bool(cookie.get("url"))
    if not (has_domain or has_url):
        raise CookieFormatError("Cookie must include either 'domain' or 'url'")


def validate_cookies(cookies: Cookies) -> None:
    """
    RU: Валидация входных cookies на границе библиотеки.
        Ошибки формата должны быть обнаружены до старта фич-логики.

    EN: Validate input cookies at the library boundary.
        Format errors should be caught before feature logic runs.
    """
    if not isinstance(cookies, Sequence):
        raise CookieFormatError("cookies must be a sequence of cookie mappings")
    for c in cookies:
        if not isinstance(c, Mapping):
            raise CookieFormatError("Each cookie must be a mapping")
        _validate_cookie(c)


def inject_cookies(context: BrowserContext, cookies: Cookies) -> None:
    """
    Inject cookies into a fresh browser context.

    RU: Восстановление сессии. Chrome-shaped cookies конвертируются на границе Playwright.
    EN: Session restore. Chrome-shaped cookies are converted at the Playwright boundary.
    """
    if not cookies:
        return
    converted = _to_playwright_if_needed(list(cookies))
    validate_cookies(converted)
    context.add_cookies(converted)


def extract_cookies(context: BrowserContext) -> list[dict[str, Any]]:
    """
    RU: Экспорт cookies из текущего browser context (Playwright list).
        Chrome-shaped persist делает вызывающая сторона через session_snapshot.export_session.
    EN: Export Playwright cookies. Chrome-shaped persist is done by the caller via export_session.
    """
    return context.cookies()


def _to_playwright_if_needed(cookies: list[Any]) -> list[dict[str, Any]]:
    raw = [c for c in cookies if isinstance(c, Mapping)]
    if not raw:
        return []
    looks_chrome = any(
        isinstance(c, Mapping) and "expirationDate" in c and "expires" not in c for c in raw
    )
    if not looks_chrome:
        return [dict(c) for c in raw]
    try:
        from session_snapshot import to_playwright_cookies
    except ImportError:
        return [dict(c) for c in raw]
    converted = to_playwright_cookies([dict(c) for c in raw])
    return converted if converted else [dict(c) for c in raw]

