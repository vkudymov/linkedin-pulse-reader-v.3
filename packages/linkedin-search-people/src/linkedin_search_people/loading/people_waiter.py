from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from linkedin_search_core.exceptions import FeedLoadError


@dataclass(frozen=True, slots=True)
class PeopleWaiter:
    timeout_ms: int

    container_selectors: tuple[str, ...] = (
        "main[role='main']",
        "div.search-results-container",
        "div.application-outlet",
        "div#main",
        "body",
    )

    card_anchor_selector: str = (
        "div.reusable-search__result-container, "
        "li.reusable-search__result-container, "
        "div[data-chameleon-result-urn], "
        "a[href*='/in/']"
    )

    def wait_for_people_ready(self, page: Page) -> None:
        deadline = time.time() + (self.timeout_ms / 1000.0)
        self._wait_for_any_selector(page, self.container_selectors, deadline, state="attached")
        remaining_ms = max(500, int((deadline - time.time()) * 1000))
        try:
            page.wait_for_selector(self.card_anchor_selector, timeout=remaining_ms, state="attached")
        except PlaywrightTimeoutError as e:
            raise FeedLoadError("People search results did not appear.") from e

    def wait_for_profile_ready(self, page: Page) -> None:
        deadline = time.time() + (self.timeout_ms / 1000.0)
        remaining_ms = max(500, int((deadline - time.time()) * 1000))
        try:
            page.wait_for_selector(
                "h1, main[role='main'] h1, section.pv-top-card, "
                "div.pv-top-card, a[href*='/in/']",
                timeout=remaining_ms,
                state="attached",
            )
        except PlaywrightTimeoutError as e:
            raise FeedLoadError("LinkedIn profile did not load.") from e

    @staticmethod
    def _wait_for_any_selector(
        page: Page,
        selectors: tuple[str, ...],
        deadline: float,
        *,
        state: str,
    ) -> None:
        last_error: Exception | None = None
        for selector in selectors:
            remaining_ms = max(200, int((deadline - time.time()) * 1000))
            if remaining_ms <= 0:
                break
            try:
                page.wait_for_selector(selector, timeout=remaining_ms, state=state)  # type: ignore[arg-type]
                return
            except PlaywrightTimeoutError as e:
                last_error = e
        raise FeedLoadError("People search layout did not appear.") from last_error
