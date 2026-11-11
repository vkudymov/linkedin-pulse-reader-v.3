from __future__ import annotations

import logging
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from linkedin_search_core.exceptions import LoginRequiredError
from linkedin_search_people.navigation.people_search_url import build_people_search_url

log = logging.getLogger(__name__)

_session_is_logged_out: Any
try:
    from session_snapshot import is_logged_out as _session_is_logged_out
except ImportError:  # pragma: no cover
    _session_is_logged_out = None


@dataclass(frozen=True, slots=True)
class PeopleNavigator:
    base_url: str = "https://www.linkedin.com/search/results/people/"

    def goto_search(
        self,
        page: Page,
        *,
        keywords: str,
        filters: Mapping[str, Any] | None = None,
    ) -> None:
        url = build_people_search_url(base_url=self.base_url, keywords=keywords, filters=filters)
        try:
            page.goto(url, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            page.goto(url, wait_until="commit")
        except PlaywrightError as e:
            raise LoginRequiredError(f"LinkedIn people search did not open: {e}") from e

        with suppress(Exception):
            page.wait_for_selector(
                "main[role='main'], div.search-results-container, "
                "a[href*='/in/'], "
                "input#username, input[name='session_key'], input[name='session_password']",
                timeout=10_000,
            )

        if self._looks_like_login_page(page) or self._is_auth_redirect(page.url):
            raise LoginRequiredError(
                "LinkedIn returned a login/authwall page for the people search URL. "
                "Provide valid cookies or complete manual login first."
            )

    def goto_profile(self, page: Page, *, profile_url: str) -> None:
        url = (profile_url or "").strip()
        if not url:
            raise ValueError("profile_url is empty")
        try:
            page.goto(url, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            page.goto(url, wait_until="commit")
        except PlaywrightError as e:
            raise LoginRequiredError(f"LinkedIn profile did not open: {e}") from e
        if self._looks_like_login_page(page) or self._is_auth_redirect(page.url):
            raise LoginRequiredError("LinkedIn returned a login/authwall page for the profile URL.")

    def _looks_like_login_page(self, page: Page) -> bool:
        url = page.url or ""
        if self._is_auth_redirect(url):
            return True
        if callable(_session_is_logged_out):
            with suppress(Exception):
                if _session_is_logged_out(page):
                    return True
        with suppress(Exception):
            if page.locator("input#username, input[name='session_key']").count() > 0:
                return True
        return False

    @staticmethod
    def _is_auth_redirect(url: str) -> bool:
        u = (url or "").lower()
        return any(x in u for x in ("/login", "/checkpoint", "/authwall", "session_redirect"))
