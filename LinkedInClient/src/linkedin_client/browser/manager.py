from __future__ import annotations

"""
RU: Browser lifecycle (platform layer).
    Инкапсулирует запуск/остановку Playwright+Chromium и выдаёт готовые `Context/Page`.
    Остальные модули не должны управлять lifecycle — только работать с уже созданной страницей.

EN: Browser lifecycle (platform layer).
    Encapsulates Playwright+Chromium startup/teardown and provides a ready `Context/Page`.
    Other modules must not manage lifecycle — they only operate on the provided page.
"""

from dataclasses import dataclass

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from ..exceptions import BrowserLifecycleError
from .config import BrowserConfig


@dataclass(slots=True)
class BrowserHandle:
    """
    RU: Пакет связанных runtime-ресурсов Playwright (Playwright/Browser/Context/Page).
    EN: A bundle of related Playwright runtime resources (Playwright/Browser/Context/Page).
    """
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


class BrowserManager:
    """
    RU: Владелец browser lifecycle для одного `LinkedInClient` запуска.
        Нужен для безопасного teardown и предсказуемого управления ресурсами.

    EN: Owns browser lifecycle for a single `LinkedInClient` session.
        Ensures safe teardown and predictable resource management.
    """
    def __init__(self, config: BrowserConfig) -> None:
        self._config = config
        self._handle: BrowserHandle | None = None

    @property
    def handle(self) -> BrowserHandle:
        if self._handle is None:
            raise BrowserLifecycleError("Browser not started. Use LinkedInClient as a context manager.")
        return self._handle

    def start(self) -> BrowserHandle:
        if self._handle is not None:
            raise BrowserLifecycleError("Browser already started.")

        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=self._config.headless,
            slow_mo=self._config.slow_mo_ms,
        )

        context = browser.new_context(
            locale=self._config.locale,
            timezone_id=self._config.timezone_id,
            user_agent=self._config.user_agent,
            viewport={"width": self._config.viewport_width, "height": self._config.viewport_height},
        )
        context.set_default_timeout(self._config.timeout_ms)
        context.set_default_navigation_timeout(self._config.timeout_ms)

        page = context.new_page()

        self._handle = BrowserHandle(playwright=pw, browser=browser, context=context, page=page)
        return self._handle

    def close(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is None:
            return

        close_errors: list[Exception] = []
        for closer in (handle.page.close, handle.context.close, handle.browser.close):
            try:
                closer()
            except Exception as e:  # pragma: no cover (best-effort cleanup)
                close_errors.append(e)

        try:
            handle.playwright.stop()
        except Exception as e:  # pragma: no cover
            close_errors.append(e)

        if close_errors:
            raise BrowserLifecycleError("Browser shutdown encountered errors.") from close_errors[0]

