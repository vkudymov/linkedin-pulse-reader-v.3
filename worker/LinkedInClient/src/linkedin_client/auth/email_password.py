from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from playwright.sync_api import BrowserContext, Page

from .wait import SessionWaitConfig, wait_for_session


@dataclass(frozen=True, slots=True)
class EmailPasswordLoginParams:
    identifier: str | None
    password: str | None


class EmailPasswordLoginFlow:
    """
    Best-effort email/phone + password automation for LinkedIn login form.

    If params are missing, the flow keeps the UI open and only waits for the user
    to complete login (same behavior as manual flow).
    """

    def __init__(
        self,
        *,
        timeout_ms: int,
        params: EmailPasswordLoginParams,
        cancelled: Callable[[], bool] | None = None,
        on_checkpoint: Callable[[], None] | None = None,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._params = params
        self._cancelled = cancelled
        self._on_checkpoint = on_checkpoint

    def run(self, page: Page, context: BrowserContext) -> None:
        identifier = (self._params.identifier or "").strip()
        password = self._params.password or ""

        if identifier and password:
            self._fill_and_submit(page, identifier=identifier, password=password)

        wait_for_session(
            page,
            cfg=SessionWaitConfig(
                timeout_ms=self._timeout_ms,
                cancelled=self._cancelled,
                on_checkpoint=self._on_checkpoint,
            ),
        )

    @staticmethod
    def _fill_and_submit(page: Page, *, identifier: str, password: str) -> None:
        # LinkedIn uses slightly different selectors depending on the variant of login page.
        user_sel = "input#username, input[name='session_key']"
        pass_sel = "input#password, input[name='session_password']"

        page.wait_for_selector(user_sel, timeout=10_000)
        page.locator(user_sel).first.fill(identifier)
        page.locator(pass_sel).first.fill(password)

        # Submit: prefer explicit button, fallback to form submit.
        if page.locator("button[type='submit']").count() > 0:
            page.locator("button[type='submit']").first.click()
        else:
            page.keyboard.press("Enter")

