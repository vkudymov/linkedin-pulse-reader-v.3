from __future__ import annotations

"""
RU: Главный orchestration-модуль библиотеки.
    `LinkedInClient` — boundary/facade: внешние проекты используют только его, а внутренние слои
    (browser/auth/navigation/loading/parsing) остаются заменяемыми и тестируемыми.

EN: Library orchestration module.
    `LinkedInClient` is the boundary/facade: callers interact with it, while internal layers
    (browser/auth/navigation/loading/parsing) remain swappable and testable.
"""

from contextlib import suppress
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from dataclasses import replace
from playwright.sync_api import Page, BrowserContext

from .auth.email_password import EmailPasswordLoginFlow, EmailPasswordLoginParams
from .auth.methods import LoginMethod
from .auth.social import SocialLoginFlow, SocialLoginParams
from .browser import BrowserConfig, BrowserManager
from .exceptions import BrowserLifecycleError, LinkedInClientError
from .config import LinkedInClientConfig


class LinkedInSession:
    """
    RU: Краткое описание
        `LinkedInClient` — публичный фасад библиотеки и основная точка входа для интеграции
        с LinkedIn через Playwright (Chromium). Он предоставляет единый, стабильный интерфейс
        для сценариев автоматизации, оставаясь максимально stateless: библиотека не хранит
        учётные данные и не персистит cookies.

    RU: Архитектурная роль
        Оркестратор (Facade/Orchestrator), который управляет жизненным циклом браузера,
        собирает вместе навигацию, ожидания загрузки, скроллинг и парсинг, и возвращает
        доменные модели наружу. `LinkedInClient` является boundary-слоем библиотеки:
        внешние проекты взаимодействуют с ним, не зная о внутренней структуре модулей.

    RU: Ответственность в системе
        - Управлять session-bound ресурсами (Playwright/Browser/Context/Page) внутри `with`-блока.
        - Принимать cookies на вход (если есть) и обеспечивать их корректное использование в контексте.
        - Обеспечивать путь к интерактивной аутентификации (manual login) и отдавать актуальные cookies
          вызывающему приложению для дальнейшего хранения.
        - Выполнять высокоуровневые пользовательские операции (например, получение постов) и возвращать
          структурированные объекты, изолируя пользователя от нестабильного DOM LinkedIn.

    RU: Взаимодействие с другими компонентами
        - `BrowserManager`: владение жизненным циклом Chromium/Context/Page.
        - auth/cookies: session restore via session_snapshot (no persistence).
        - `FeedNavigator`: переход на целевую страницу и обнаружение auth-редиректов.
        - `FeedWaiter`/`HumanScroller`: стабилизация динамической страницы и догрузка контента.
        - `PostParser`: преобразование DOM-элементов в `Post` модели.
        Пользователь библиотеки должен работать через `LinkedInClient` как через context manager,
        передавая cookies при наличии и сохраняя обновлённые cookies на своей стороне.

    EN: Short description
        `LinkedInClient` is the library’s public facade and the primary integration entrypoint
        for automating LinkedIn via Playwright (Chromium). It intentionally stays as stateless
        as possible: the library does not persist credentials and does not store cookies.

    EN: Architectural role
        An Orchestrator/Facade that owns the browser lifecycle and composes navigation, waiting,
        scrolling, and parsing into high-level operations. `LinkedInClient` acts as the boundary
        of the library: external applications use it without coupling to internal modules.

    EN: System responsibilities
        - Own session-scoped resources (Playwright/Browser/Context/Page) within the `with` block.
        - Accept cookies as input (when available) and ensure they are applied to the browser context.
        - Support interactive authentication (manual login) and return fresh cookies to the caller
          for external persistence.
        - Execute high-level operations (e.g., fetching feed posts) and return structured domain objects,
          shielding callers from LinkedIn DOM volatility.

    EN: Collaboration with other components
        - `BrowserManager`: Chromium/Context/Page lifecycle ownership.
        - auth/cookies: session restore via session_snapshot (no persistence).
        - `FeedNavigator`: navigation to target pages and auth redirect detection.
        - `FeedWaiter`/`HumanScroller`: dynamic page stabilization and content loading.
        - `PostParser`: mapping DOM elements into `Post` models.
        Library users should interact with LinkedIn exclusively through `LinkedInClient` as a context
        manager, provide cookies when available, and persist refreshed cookies in the calling application.

    The library intentionally does not manage users or persist cookies. The calling application
    provides cookies (optional) and receives cookies back after manual login.
    """

    def __init__(
        self,
        *,
        cookies: Sequence[Mapping[str, Any]] | None = None,
        session_snapshot: dict[str, Any] | None = None,
        config: LinkedInClientConfig | None = None,
        headless: bool = True,
        timeout_ms: int = 30_000,
        slow_mo_ms: int | None = None,
    ) -> None:
        self._initial_cookies = cookies
        self._session_snapshot = _coerce_session_snapshot(session_snapshot, cookies)
        if config is None:
            browser_cfg = BrowserConfig(
                headless=headless, timeout_ms=timeout_ms, slow_mo_ms=slow_mo_ms
            )
            self._client_cfg = LinkedInClientConfig(browser=browser_cfg)
        else:
            self._client_cfg = config
        self._client_cfg = _apply_snapshot_browser_options(self._client_cfg, self._session_snapshot)

        self._browser = BrowserManager(self._client_cfg.browser)

        self._entered = False
        self._login_page_opened = False
        self._manual_login_completed = False

    def __enter__(self) -> LinkedInSession:
        if self._entered:
            raise BrowserLifecycleError("LinkedInClient cannot be re-entered.")
        self._entered = True

        handle = self._browser.start()
        snapshot_cookies = (
            self._session_snapshot.get("cookies")
            if isinstance(self._session_snapshot, dict)
            else None
        )
        if isinstance(snapshot_cookies, list) and snapshot_cookies:
            _restore_session_snapshot(handle.context, handle.page, self._session_snapshot)
        else:
            # No cookies provided: open LinkedIn login page for manual authentication.
            handle.page.goto(
                "https://www.linkedin.com/login", wait_until="domcontentloaded"
            )
            self._login_page_opened = True

        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self._browser.close()
        finally:
            self._entered = False

    @property
    def page(self) -> Page:
        return self._browser.handle.page

    @property
    def context(self) -> BrowserContext:
        return self._browser.handle.context

    def login_and_get_cookies(
        self,
        *,
        method: LoginMethod = LoginMethod.email,
        identifier: str | None = None,
        password: str | None = None,
        cancelled: Callable[[], bool] | None = None,
        on_checkpoint: Callable[[], None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        RU: Интерактивная аутентификация (UI -> cookies).
            Возвращаем cookies наружу, чтобы вызывающее приложение могло их сохранить.
            Варианты:
              - email/phone + password (best-effort автозаполнение)
              - Google
              - Apple ID

        EN: Interactive session recovery (UI -> cookies).
            Cookies are returned to the caller for external persistence.
        """
        if not self._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        if self._initial_cookies or _snapshot_has_cookies(self._session_snapshot):
            raise LinkedInClientError(
                "Cookies were provided; manual login is not supported in this mode."
            )
        if self._manual_login_completed:
            return [dict(c) for c in self._browser.handle.context.cookies()]

        # Ensure we're on the LinkedIn login page before starting a UI flow.
        with suppress(Exception):
            self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        timeout_ms = self._client_cfg.browser.timeout_ms
        ctx = self._browser.handle.context

        if method == LoginMethod.email:
            flow_email = EmailPasswordLoginFlow(
                timeout_ms=timeout_ms,
                params=EmailPasswordLoginParams(identifier=identifier, password=password),
                cancelled=cancelled,
                on_checkpoint=on_checkpoint,
            )
            flow_email.run(page=self.page, context=ctx)
        elif method in (LoginMethod.google, LoginMethod.apple):
            flow_social = SocialLoginFlow(
                timeout_ms=timeout_ms,
                params=SocialLoginParams(method=method),
                cancelled=cancelled,
                on_checkpoint=on_checkpoint,
            )
            flow_social.run(page=self.page, context=ctx)
        else:
            raise LinkedInClientError(f"Unsupported login method: {method!r}")

        self._manual_login_completed = True
        return [dict(c) for c in ctx.cookies()]

    def get_cookies(self) -> list[dict[str, Any]]:
        """
        Playwright cookie list from the current context.
        Pulse persist uses export_session_snapshot, not this method.
        """
        if not self._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        return [dict(c) for c in self._browser.handle.context.cookies()]

    def export_session_snapshot(self, base: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Chrome-shaped session snapshot for Pulse persist. Raises SessionLoggedOutError
        on login-wall URLs (caller should not save-back).
        """
        if not self._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        from session_snapshot import export_session

        return export_session(
            self.context,
            self.page,
            base if isinstance(base, dict) else (self._session_snapshot or {}),
        )

    def is_logged_in(self) -> bool:
        if not self._entered:
            return False
        try:
            from session_snapshot import has_auth_cookie, is_logged_out
        except ImportError:
            url = self.page.url.lower()
            return (
                "linkedin.com/feed" in url
                and "login" not in url
                and "checkpoint" not in url
            )
        if is_logged_out(self.page.url):
            return False
        try:
            return has_auth_cookie([dict(c) for c in self.context.cookies()])
        except Exception:
            return False


def _snapshot_has_cookies(snapshot: dict[str, Any] | None) -> bool:
    if not isinstance(snapshot, dict):
        return False
    cookies = snapshot.get("cookies")
    return isinstance(cookies, list) and len(cookies) > 0


def _coerce_session_snapshot(
    session_snapshot: dict[str, Any] | None,
    cookies: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any] | None:
    if isinstance(session_snapshot, dict):
        return session_snapshot
    if cookies:
        raw = [dict(c) for c in cookies if isinstance(c, dict)]
        try:
            from session_snapshot import playwright_list_to_snapshot

            return playwright_list_to_snapshot(raw)
        except ImportError:
            return {"cookies": raw}
    return None


def _apply_snapshot_browser_options(
    config: LinkedInClientConfig,
    snapshot: dict[str, Any] | None,
) -> LinkedInClientConfig:
    if not isinstance(snapshot, dict):
        return config
    try:
        from session_snapshot import playwright_context_options
    except ImportError:
        return config
    opts = playwright_context_options(snapshot)
    if not opts:
        return config
    browser = config.browser
    updates: dict[str, Any] = {}
    if opts.get("user_agent"):
        updates["user_agent"] = opts["user_agent"]
    if opts.get("locale"):
        updates["locale"] = opts["locale"]
    viewport = opts.get("viewport")
    if isinstance(viewport, dict):
        width = viewport.get("width")
        height = viewport.get("height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            updates["viewport_width"] = width
            updates["viewport_height"] = height
    if not updates:
        return config
    return replace(config, browser=replace(browser, **updates))


def _restore_session_snapshot(context: BrowserContext, page: Page, snapshot: dict[str, Any] | None) -> None:
    if not isinstance(snapshot, dict):
        return
    try:
        from session_snapshot import restore_session
    except ImportError as e:
        raise BrowserLifecycleError(
            "session_snapshot is required to restore a LinkedIn session."
        ) from e
    restore_session(context, page, snapshot)
