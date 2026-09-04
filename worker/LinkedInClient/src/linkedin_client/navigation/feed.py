from __future__ import annotations

"""
RU: Навигация к LinkedIn feed и детекция auth-редиректов.
    Модуль отделяет “куда перейти” от ожиданий/скролла/парсинга и явно сигнализирует об отсутствии
    авторизации через `LoginRequiredError`.

EN: Navigation to LinkedIn feed and auth-redirect detection.
    Separates “where to go” from waiting/scrolling/parsing and explicitly signals missing auth via
    `LoginRequiredError`.
"""

from contextlib import suppress
from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ..exceptions import FeedLoadError, LoginRequiredError

try:
    from session_snapshot import is_logged_out as _session_is_logged_out
except ImportError:  # pragma: no cover
    _session_is_logged_out = None


@dataclass(frozen=True, slots=True)
class FeedNavigator:
    """
    RU: Роутер фичи “feed”.
        Используется оркестратором перед ожиданиями/скроллом/парсингом, чтобы гарантировать корректную
        целевую страницу.

    EN: Feed feature router.
        Used by the orchestrator before waiting/scrolling/parsing to ensure the correct target page.
    """
    feed_url: str = "https://www.linkedin.com/feed/"

    def goto_feed(self, page: Page) -> None:
        # If we're already on /feed, avoid re-navigation (LinkedIn can be slow/flaky on reload).
        try:
            current = (page.url or "").lower()
        except Exception:
            current = ""

        if "linkedin.com/feed" not in current:
            try:
                page.goto(self.feed_url, wait_until="domcontentloaded")
            except PlaywrightTimeoutError:
                # Fallback: LinkedIn may keep the document "loading" for a long time.
                # We only need the navigation to commit; readiness is handled by waiter/selectors.
                try:
                    page.goto(self.feed_url, wait_until="commit")
                except PlaywrightError as e:
                    raise FeedLoadError(_feed_open_error_message(e)) from e
            except PlaywrightError as e:
                raise FeedLoadError(_feed_open_error_message(e)) from e

        # LinkedIn may serve authwall/login UI for /feed without changing the URL immediately.
        # Wait briefly for either feed layout or login markers, then decide.
        with suppress(Exception):
            page.wait_for_selector(
                "main[role='main'], div.application-outlet, "
                "input#username, input[name='session_key'], input[name='session_password']",
                timeout=10_000,
            )

        if self._looks_like_login_page(page) or self._looks_like_checkpoint_page(page):
            raise LoginRequiredError(
                "LinkedIn returned a login/authwall page for the feed URL. "
                "Provide valid cookies or complete manual login first."
            )
        if self._is_auth_redirect(page.url):
            raise LoginRequiredError(
                "LinkedIn redirected to an authentication/checkpoint page. "
                "Provide valid cookies or complete manual login first."
            )

    @staticmethod
    def _is_auth_redirect(url: str) -> bool:
        if _session_is_logged_out is not None:
            return bool(_session_is_logged_out(url or ""))
        lowered = (url or "").lower()
        return any(
            marker in lowered
            for marker in (
                "/login",
                "/checkpoint",
                "/authwall",
                "linkedin.com/uas/",
            )
        )

    @staticmethod
    def _looks_like_login_page(page: Page) -> bool:
        """
        RU: LinkedIn может отдавать страницу логина даже на /feed (URL не всегда меняется).
        EN: LinkedIn may serve a login page even on /feed (URL does not always change).
        """
        with suppress(Exception):
            title = (page.title() or "").lower()
            if "sign in" in title or "login" in title:
                return True

        try:
            # Login form markers (avoid user content / PII).
            return page.locator(
                "input#username, input[name='session_key'], input[name='session_password']"
            ).count() > 0
        except Exception:
            return False

    @staticmethod
    def _looks_like_checkpoint_page(page: Page) -> bool:
        """
        RU: Иногда LinkedIn показывает checkpoint/verification UI, при этом URL может оставаться /feed.
        EN: LinkedIn may show checkpoint/verification UI while the URL still looks like /feed.
        """
        try:
            return (
                page.locator(
                    "form[action*='checkpoint'], input[name='challengeId'], input[name='pin']"
                ).count()
                > 0
            )
        except Exception:
            return False


def _safe_url(url: str) -> str:
    # Avoid logging full URLs with params/fragments.
    try:
        from urllib.parse import urlparse

        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}"
    except Exception:
        return url


def _feed_open_error_message(error: Exception) -> str:
    detail = str(error).splitlines()[0] if str(error).strip() else type(error).__name__
    return (
        "LinkedIn feed did not open: https://www.linkedin.com/feed/. "
        "Check internet connection, VPN/proxy, and that LinkedIn opens in a regular browser. "
        f"Playwright error: {detail}"
    )


def _safe_title(page: Page) -> str:
    try:
        t = page.title()
        return t[:120]
    except Exception:
        return ""

