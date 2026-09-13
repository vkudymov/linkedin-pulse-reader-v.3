from __future__ import annotations

"""
Jobs search readiness policy (best-effort).
Keeps the same design goals as FeedWaiter: detect that the main layout is present and that
at least one job-card anchor exists before parsing/clicking.
"""

import time
from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ..exceptions import FeedLoadError


@dataclass(frozen=True, slots=True)
class JobsWaiter:
    timeout_ms: int

    container_selectors: tuple[str, ...] = (
        "main[role='main']",
        "div[role='main']",
        "div.application-outlet",
        "div#react-root",
        "body",
    )

    job_card_anchor_selector: str = "a[href*='/jobs/view/']"

    def wait_for_jobs_ready(self, page: Page) -> None:
        deadline = time.time() + (self.timeout_ms / 1000.0)
        self._wait_for_any_selector(page, self.container_selectors, deadline, state="attached")

        remaining_ms = max(0, int((deadline - time.time()) * 1000))
        try:
            page.wait_for_selector(
                self.job_card_anchor_selector,
                timeout=min(remaining_ms, 10_000),
                state="attached",
            )
        except PlaywrightTimeoutError as e:
            # Best-effort: LinkedIn may show "no results" variants; allow parser to handle empty.
            raise FeedLoadError(f"Jobs page did not become ready: {e}") from e

    def current_job_count(self, page: Page) -> int:
        try:
            return page.locator(self.job_card_anchor_selector).count()
        except Exception:
            return 0

    def _wait_for_any_selector(
        self,
        page: Page,
        selectors: tuple[str, ...],
        deadline: float,
        *,
        state: Literal["attached", "detached", "hidden", "visible"] = "visible",
    ) -> None:
        last_error: Exception | None = None
        for idx, sel in enumerate(selectors):
            remaining_ms = max(0, int((deadline - time.time()) * 1000))
            if remaining_ms <= 0:
                break
            try:
                selectors_left = max(1, len(selectors) - idx)
                used_timeout = max(1, int(remaining_ms / selectors_left))
                page.wait_for_selector(sel, timeout=used_timeout, state=state)
                return
            except Exception as e:  # noqa: BLE001 - best-effort across fallbacks
                last_error = e
                continue

        raise FeedLoadError(f"Jobs layout did not appear before timeout: {last_error}")

