from __future__ import annotations

"""
RU: Browser lifecycle (platform layer).
    Инкапсулирует запуск/остановку Playwright+Chromium и выдаёт готовые `Context/Page`.
    Остальные модули не должны управлять lifecycle — только работать с уже созданной страницей.

EN: Browser lifecycle (platform layer).
    Encapsulates Playwright+Chromium startup/teardown and provides a ready `Context/Page`.
    Other modules must not manage lifecycle — they only operate on the provided page.
"""

from contextlib import suppress
from dataclasses import dataclass

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from ..exceptions import BrowserLifecycleError
from .config import BrowserConfig


@dataclass(slots=True)
class BrowserHandle:
    """
    RU: Пакет связанных runtime-ресурсов Playwright (Playwright/Browser/Context/Page).
    EN: A bundle of related Playwright runtime resources (Playwright/Browser/Context/Page).
    """
    playwright: Playwright
    browser: Browser | None
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
        args = list(self._config.launch_args or [])
        # Common mitigation for OAuth flows: reduce obvious automation markers.
        if "--disable-blink-features=AutomationControlled" not in args:
            args.append("--disable-blink-features=AutomationControlled")

        if self._config.user_data_dir:
            context = _launch_persistent_context(pw, self._config, args=args)
            browser = getattr(context, "browser", None)
        else:
            browser = _launch_browser(pw, self._config, args=args)
            context = browser.new_context(
                locale=self._config.locale,
                timezone_id=self._config.timezone_id,
                user_agent=self._config.user_agent,
                viewport={"width": self._config.viewport_width, "height": self._config.viewport_height},
            )

        # Reduce webdriver detection (best-effort; does not guarantee stealth).
        with suppress(Exception):
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

        context.set_default_timeout(self._config.timeout_ms)
        context.set_default_navigation_timeout(self._config.timeout_ms)

        page = context.pages[0] if context.pages else context.new_page()

        self._handle = BrowserHandle(playwright=pw, browser=browser, context=context, page=page)
        return self._handle

    def close(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is None:
            return

        close_errors: list[Exception] = []
        closers = [handle.page.close, handle.context.close]
        if handle.browser is not None:
            closers.append(handle.browser.close)

        for closer in closers:
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


def _launch_browser(pw: Playwright, cfg: BrowserConfig, *, args: list[str]) -> Browser:
    try:
        return pw.chromium.launch(
            headless=cfg.headless,
            slow_mo=cfg.slow_mo_ms,
            channel=cfg.channel,
            args=args or None,
        )
    except PlaywrightError:
        return pw.chromium.launch(
            headless=cfg.headless,
            slow_mo=cfg.slow_mo_ms,
            args=args or None,
        )


def _launch_persistent_context(
    pw: Playwright,
    cfg: BrowserConfig,
    *,
    args: list[str],
) -> BrowserContext:
    try:
        return pw.chromium.launch_persistent_context(
            user_data_dir=cfg.user_data_dir,
            headless=cfg.headless,
            slow_mo=cfg.slow_mo_ms,
            channel=cfg.channel,
            args=args or None,
            locale=cfg.locale,
            timezone_id=cfg.timezone_id,
            user_agent=cfg.user_agent,
            viewport={"width": cfg.viewport_width, "height": cfg.viewport_height},
        )
    except PlaywrightError:
        return pw.chromium.launch_persistent_context(
            user_data_dir=cfg.user_data_dir,
            headless=cfg.headless,
            slow_mo=cfg.slow_mo_ms,
            args=args or None,
            locale=cfg.locale,
            timezone_id=cfg.timezone_id,
            user_agent=cfg.user_agent,
            viewport={"width": cfg.viewport_width, "height": cfg.viewport_height},
        )

