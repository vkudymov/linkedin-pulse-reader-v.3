from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ..exceptions import LoginRequiredError

_session_is_logged_out: Any
try:
    from session_snapshot import is_logged_out as _session_is_logged_out
except ImportError:  # pragma: no cover
    _session_is_logged_out = None


@dataclass(frozen=True, slots=True)
class JobsNavigator:
    base_url: str = "https://www.linkedin.com/jobs/search/"

    def goto_search(self, page: Page, *, keywords: str, location: str | None) -> None:
        q: dict[str, str] = {"keywords": keywords}
        if location:
            q["location"] = location
        url = f"{self.base_url}?{urlencode(q)}"

        try:
            page.goto(url, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            # LinkedIn can keep the document in loading; commit is enough for waiter/selectors.
            page.goto(url, wait_until="commit")
        except PlaywrightError as e:
            raise LoginRequiredError(f"LinkedIn jobs search did not open: {e}") from e

        with suppress(Exception):
            page.wait_for_selector(
                "main[role='main'], div.application-outlet, "
                "a[href*='/jobs/view/'], "
                "input#username, input[name='session_key'], input[name='session_password']",
                timeout=10_000,
            )

        if self._looks_like_login_page(page) or self._is_auth_redirect(page.url):
            raise LoginRequiredError(
                "LinkedIn returned a login/authwall page for the jobs search URL. "
                "Provide valid cookies or complete manual login first."
            )

    @staticmethod
    def _is_auth_redirect(url: str) -> bool:
        if _session_is_logged_out is not None:
            return bool(_session_is_logged_out(url or ""))
        lowered = (url or "").lower()
        return any(marker in lowered for marker in ("/login", "/checkpoint", "/authwall", "linkedin.com/uas/"))

    @staticmethod
    def _looks_like_login_page(page: Page) -> bool:
        with suppress(Exception):
            title = (page.title() or "").lower()
            if "sign in" in title or "login" in title:
                return True
        try:
            return page.locator(
                "input#username, input[name='session_key'], input[name='session_password']"
            ).count() > 0
        except Exception:
            return False

