from __future__ import annotations

"""
RU: Manual login fallback.
    Используется когда cookies отсутствуют/протухли: пользователь логинится в UI, библиотека извлекает
    cookies и отдаёт их наружу для сохранения (сама библиотека cookies не хранит).

EN: Manual login fallback.
    Used when cookies are missing/expired: the user signs in via UI, the library extracts cookies and
    returns them to the caller for persistence (the library does not store cookies).
"""

from dataclasses import dataclass

from playwright.sync_api import BrowserContext, Page

from .cookies import extract_cookies
from .wait import SessionWaitConfig, wait_for_session


@dataclass(frozen=True, slots=True)
class LoginResult:
    cookies: list[dict]


class ManualLoginFlow:
    """
    RU: Интерактивное восстановление сессии (UI -> cookies).
    EN: Interactive session recovery (UI -> cookies).
    """
    LOGIN_URL = "https://www.linkedin.com/login"
    FEED_URL = "https://www.linkedin.com/feed/"

    def __init__(self, timeout_ms: int) -> None:
        self._timeout_ms = timeout_ms

    def run(self, page: Page, context: BrowserContext) -> LoginResult:
        page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
        wait_for_session(page, cfg=SessionWaitConfig(timeout_ms=self._timeout_ms))

        # We intentionally do not validate feed readiness here; downstream navigation/waiting
        # will re-stabilize. At this point LinkedIn has redirected to feed, so cookies are usable.
        cookies = extract_cookies(context)
        return LoginResult(cookies=cookies)

