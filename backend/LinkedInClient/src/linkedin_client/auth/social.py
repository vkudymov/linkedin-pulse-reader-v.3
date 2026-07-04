from __future__ import annotations

import re
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from .methods import LoginMethod
from .wait import SessionWaitConfig, wait_for_session


@dataclass(frozen=True, slots=True)
class SocialLoginParams:
    method: LoginMethod


class SocialLoginFlow:
    """
    Social provider login entry (Google / Apple) on the LinkedIn login page.

    The OAuth step is intentionally interactive: the user may need to complete
    CAPTCHA/2FA in the opened browser. This flow only clicks the provider button
    and waits until LinkedIn feed becomes available.
    """

    def __init__(
        self,
        *,
        timeout_ms: int,
        params: SocialLoginParams,
        cancelled: Callable[[], bool] | None = None,
        on_checkpoint: Callable[[], None] | None = None,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._params = params
        self._cancelled = cancelled
        self._on_checkpoint = on_checkpoint

    def run(self, page: Page, context: BrowserContext) -> None:
        # LinkedIn can open OAuth in a popup or do a same-tab redirect.
        # We click once and (best-effort) capture the popup if it appears.
        with suppress(PlaywrightTimeoutError):
            with context.expect_page(timeout=2_000) as pinfo:
                self._click_provider_button(page)
            popup = pinfo.value
            with suppress(Exception):
                popup.bring_to_front()

        wait_for_session(
            page,
            cfg=SessionWaitConfig(
                timeout_ms=self._timeout_ms,
                cancelled=self._cancelled,
                on_checkpoint=self._on_checkpoint,
            ),
        )

    def _click_provider_button(self, page: Page) -> None:
        name_rx = self._provider_button_name_regex()

        # Prefer accessible role-based selectors.
        with suppress(Exception):
            btn = page.get_by_role("button", name=name_rx)
            if btn.count() > 0:
                btn.first.click()
                return

        # Fallback selectors observed on some LinkedIn variants.
        candidates = self._provider_fallback_selectors()
        for sel in candidates:
            with suppress(Exception):
                loc = page.locator(sel)
                if loc.count() > 0:
                    loc.first.click()
                    return

        # Last resort: click by text.
        with suppress(Exception):
            page.get_by_text(name_rx).first.click()
            return

        raise RuntimeError(f"Could not find LinkedIn {self._params.method} login button.")

    def _provider_button_name_regex(self) -> re.Pattern[str]:
        if self._params.method == LoginMethod.google:
            return re.compile(r"(continue|sign)\s+in\s+with\s+google", re.IGNORECASE)
        if self._params.method == LoginMethod.apple:
            return re.compile(r"(continue|sign)\s+in\s+with\s+apple", re.IGNORECASE)
        return re.compile(r".*", re.IGNORECASE)

    def _provider_fallback_selectors(self) -> list[str]:
        if self._params.method == LoginMethod.google:
            return [
                "button[data-tracking-control-name*='google']",
                "button[aria-label*='Google' i]",
                "a[data-tracking-control-name*='google']",
            ]
        if self._params.method == LoginMethod.apple:
            return [
                "button[data-tracking-control-name*='apple']",
                "button[aria-label*='Apple' i]",
                "a[data-tracking-control-name*='apple']",
            ]
        return []

