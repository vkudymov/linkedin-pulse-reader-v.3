from __future__ import annotations

"""
RU: Ожидания и стабилизация динамической ленты.
    Определяет “готовность” страницы для дальнейших шагов (скролл/парсинг) через наблюдаемые сигналы
    DOM, чтобы снизить флейки в SPA.

EN: Waiting and stabilization for a dynamic feed.
    Defines “page readiness” for subsequent steps (scrolling/parsing) using observable DOM signals to
    reduce SPA flakiness.
"""

import time
from dataclasses import dataclass

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ..exceptions import FeedLoadError


@dataclass(frozen=True, slots=True)
class FeedWaiter:
    """
    RU: Политика готовности feed.
        Используется между навигацией и скроллом/парсингом; при проблемах поднимает `FeedLoadError`,
        чтобы оркестратор мог выполнить retry/reload.

    EN: Feed readiness policy.
        Used between navigation and scrolling/parsing; raises `FeedLoadError` so the orchestrator can
        retry/reload.
    """

    timeout_ms: int

    feed_container_selectors: tuple[str, ...] = (
        "main[role='main']",
        "div[role='main']",
        "div.application-outlet",
        "div#react-root",
        "div#content",
        "div#main",
        "main",
        "div.scaffold-layout",
        "div.scaffold-layout__content",
        "div.scaffold-layout__inner",
        "div.scaffold-layout__main",
        "div.scaffold-finite-scroll",
        "div.scaffold-finite-scroll__content",
        # Last-resort: always present once DOM is there.
        "body",
    )
    # post_container_selector_group: str = (
    #     "div.feed-shared-update-v2, "
    #     "div.occludable-update, "
    #     "article[data-urn], "
    #     "div[data-urn], "
    #     "div[data-id], "
    #     "div[data-urn*='urn:li:activity'], "
    #     "div[data-urn*='urn:li:ugcPost'], "
    #     "div[data-urn*='urn:li:share']"
    # )
    post_container_selector_group: str = "[data-testid='expandable-text-box']"
    text_selector = "[data-testid='expandable-text-box']"
    # Fallback anchors for accounts/variants where data-testid is absent.
    text_selector_fallbacks: tuple[str, ...] = (
        "div.update-components-text",
        "div.feed-shared-update-v2__description",
        "div.feed-shared-update-v2",
        "div.occludable-update",
        "article[data-urn]",
        "div[data-urn*='urn:li:activity']",
    )

    def wait_for_feed_ready(self, page: Page) -> None:
        deadline = time.time() + (self.timeout_ms / 1000.0)

        # print(
        #     "POST CONTAINERS:", self.page.locator("div.feed-shared-update-v2").count()
        # )
        # print(
        #     "TEXT BLOCKS:",
        #     self.page.locator("[data-testid='expandable-text-box']").count(),
        # )

        # 1) Ensure primary layout exists.
        # Use state="attached" here: LinkedIn containers may exist but not be considered "visible"
        # due to overlays/transitions; we only need the layout to be present before waiting for posts.
        self._wait_for_any_selector(
            page, self.feed_container_selectors, deadline, state="attached"
        )

        # 2) Best-effort: wait for at least one content anchor, but do not fail the whole flow.
        # The selector-agnostic scroll loop can still make progress and parsing can be retried later.
        remaining_ms = max(0, int((deadline - time.time()) * 1000))
        try:
            timeout_ms = min(remaining_ms, 6000)

            selector_used: str | None = None
            selectors = (self.text_selector, *self.text_selector_fallbacks)
            start = time.time()
            for sel in selectors:
                budget_ms = max(
                    1, int(timeout_ms * (1.0 - min(0.9, (time.time() - start) / 6.0)))
                )
                try:
                    page.wait_for_selector(sel, timeout=budget_ms, state="attached")
                    selector_used = sel
                    break
                except Exception:  # noqa: BLE001 - best-effort across fallbacks
                    continue

            if not selector_used:
                raise PlaywrightTimeoutError("No feed content anchor found.")
        except PlaywrightTimeoutError:
            # Best-effort: do not fail the whole run here.
            # The scroll loop + parsers can still make progress once LinkedIn finishes rendering.
            return
        # except PlaywrightTimeoutError:
        #     return

        # 3) Best-effort stabilization to reduce races while parsing.
        try:
            self._wait_for_stable_post_count(page, deadline)
        except FeedLoadError:
            return

    def wait_for_new_posts(
        self, page: Page, previous_count: int, timeout_ms: int
    ) -> int:
        deadline = time.time() + (timeout_ms / 1000.0)
        locator = page.locator(self.post_container_selector_group)
        while time.time() < deadline:
            count = locator.count()
            if count > previous_count:
                return count
            page.wait_for_timeout(250)
        return locator.count()

    def current_post_count(self, page: Page) -> int:
        return page.locator(self.post_container_selector_group).count()

    def _wait_for_any_selector(
        self,
        page: Page,
        selectors: tuple[str, ...],
        deadline: float,
        *,
        state: str = "visible",
    ) -> None:
        last_error: Exception | None = None
        for idx, sel in enumerate(selectors):
            remaining_ms = max(0, int((deadline - time.time()) * 1000))
            if remaining_ms <= 0:
                break
            try:
                # Budget remaining time across fallback selectors.
                selectors_left = max(1, len(selectors) - idx)
                used_timeout = max(1, int(remaining_ms / selectors_left))
                page.wait_for_selector(sel, timeout=used_timeout, state=state)
                return
            except Exception as e:  # noqa: BLE001 - best-effort across fallbacks
                last_error = e
                continue
        raise FeedLoadError(
            "Timed out waiting for LinkedIn feed container to load."
        ) from last_error

    def _wait_for_stable_post_count(self, page: Page, deadline: float) -> None:
        locator = page.locator(self.post_container_selector_group)
        stable_samples = 0
        last_count = -1
        while time.time() < deadline:
            count = locator.count()
            if count == last_count and count > 0:
                stable_samples += 1
                if stable_samples >= 2:
                    return
            else:
                stable_samples = 0
                last_count = count
            page.wait_for_timeout(350)
        raise FeedLoadError("Feed did not stabilize in time (post list kept changing).")
