from __future__ import annotations

import logging
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..exceptions import LoginRequiredError
from .job_search_url import build_jobs_search_url

log = logging.getLogger(__name__)

_session_is_logged_out: Any
try:
    from session_snapshot import is_logged_out as _session_is_logged_out
except ImportError:  # pragma: no cover
    _session_is_logged_out = None


@dataclass(frozen=True, slots=True)
class JobsNavigator:
    base_url: str = "https://www.linkedin.com/jobs/search/"

    def goto_search(
        self,
        page: Page,
        *,
        keywords: str,
        location: str | None,
        filters: Mapping[str, Any] | None = None,
    ) -> None:
        url = build_jobs_search_url(
            base_url=self.base_url,
            keywords=keywords,
            location=location,
            filters=filters,
        )

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

    def apply_location_first_match(self, page: Page, *, location: str | None) -> bool:
        """
        Best-effort: set the location via LinkedIn's own typeahead and pick the first suggestion.

        This avoids relying on LinkedIn's URL `location=` text guessing (which can pick the wrong
        Paris/region). We do NOT resolve geoId ourselves; LinkedIn will apply it after selection.
        """
        loc = normalize_location_text(location)
        if not loc:
            return False

        # Prefer the top search bar "Location" input (varies by locale/AB test).
        input_loc = _first_visible(
            page.locator("input[aria-label*='location' i]"),
            page.locator("input[placeholder*='location' i]"),
            page.locator("input[aria-label*='местополож' i]"),
            page.locator("input[placeholder*='местополож' i]"),
            page.locator("input[aria-label*='город' i]"),
            page.locator("input[placeholder*='город' i]"),
            page.locator("input[placeholder*='регион' i]"),
            page.locator("input[id^='jobs-search-box-location-' i]"),
            page.locator("input[id*='location' i]"),
        )
        if input_loc is None:
            log.info("jobs.apply_location: location input not found; continuing without location")
            return False

        with suppress(Exception):
            input_loc.click(timeout=1500)

        # Clear current value then type new one.
        with suppress(Exception):
            input_loc.fill("")
        with suppress(Exception):
            page.keyboard.press("Meta+A")
            page.keyboard.press("Backspace")
        with suppress(Exception):
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
        try:
            input_loc.fill(loc)
        except Exception:
            with suppress(Exception):
                input_loc.type(loc, delay=25)

        # Wait for any typeahead list, then pick first suggestion via keyboard.
        with suppress(Exception):
            page.wait_for_selector(
                "ul[role='listbox'] li, div[role='listbox'] li, "
                "ul[role='listbox'] [role='option'], div[role='listbox'] [role='option']",
                timeout=2500,
            )

        picked = False
        with suppress(Exception):
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            picked = True

        # Let LinkedIn apply the filter; avoid hard failures here.
        with suppress(Exception):
            page.wait_for_load_state("networkidle", timeout=2500)
        with suppress(Exception):
            page.wait_for_timeout(200)

        if picked:
            log.info("jobs.apply_location: picked first suggestion for location=%r", loc)
        return picked

    @staticmethod
    def _is_auth_redirect(url: str) -> bool:
        if _session_is_logged_out is not None:
            return bool(_session_is_logged_out(url or ""))
        lowered = (url or "").lower()
        markers = ("/login", "/checkpoint", "/authwall", "linkedin.com/uas/")
        return any(marker in lowered for marker in markers)

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


def normalize_location_text(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    t = value.strip()
    return t or None


def _first_visible(*locators: Locator) -> Locator | None:
    for loc in locators:
        try:
            if loc.count() <= 0:
                continue
            first = loc.first
            if first.is_visible():
                return first
        except Exception:
            continue
    return None

