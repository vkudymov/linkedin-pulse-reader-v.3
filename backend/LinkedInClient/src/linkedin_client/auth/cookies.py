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

    RU: Это основной механизм восстановления сессии без API; функция должна оставаться feature-agnostic.
    EN: This is the primary session restoration mechanism without APIs; keep it feature-agnostic.

    The library never stores cookies; it only injects them and can extract them later.
    """
    if not cookies:
        return
    validate_cookies(cookies)
    context.add_cookies(list(cookies))


def extract_cookies(context: BrowserContext) -> list[dict[str, Any]]:
    """
    RU: Экспорт cookies из текущего browser context (для внешнего хранения).
    EN: Export cookies from the current browser context (for external persistence).
    """
    return context.cookies()

