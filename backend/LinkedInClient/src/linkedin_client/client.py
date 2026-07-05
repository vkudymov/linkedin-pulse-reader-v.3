from __future__ import annotations

"""
RU: Главный orchestration-модуль библиотеки.
    `LinkedInClient` — boundary/facade: внешние проекты используют только его, а внутренние слои
    (browser/auth/navigation/loading/parsing) остаются заменяемыми и тестируемыми.

EN: Library orchestration module.
    `LinkedInClient` is the boundary/facade: callers interact with it, while internal layers
    (browser/auth/navigation/loading/parsing) remain swappable and testable.
"""

import re
from contextlib import suppress
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page

from .auth.cookies import Cookies, extract_cookies, inject_cookies
from .auth.email_password import EmailPasswordLoginFlow, EmailPasswordLoginParams
from .auth.methods import LoginMethod
from .auth.social import SocialLoginFlow, SocialLoginParams
from .browser import BrowserConfig, BrowserManager
from .config import LinkedInClientConfig
from .exceptions import BrowserLifecycleError, FeedLoadError, LinkedInClientError
from .loading import FeedWaiter, HumanScroller
from .navigation import FeedNavigator
from .parsing import PostParser
from .debug_agent_log import agent_dbg_log
from .models.post import Author, Post, merge_authors

_ACTIVITY_RE = re.compile(r"urn:li:activity:(\d+)")


def _author_from_read_item(item: dict[str, Any]) -> Author | None:
    raw = item.get("author")
    if isinstance(raw, dict):
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        headline = raw.get("headline")
        profile_url = raw.get("profile_url")
        urn = raw.get("urn")
        return Author(
            name=name.strip(),
            headline=headline if isinstance(headline, str) and headline.strip() else None,
            profile_url=(
                profile_url if isinstance(profile_url, str) and profile_url.strip() else None
            ),
            urn=urn if isinstance(urn, str) and urn.strip() else None,
        )
    if isinstance(raw, str) and raw.strip():
        return Author(name=raw.strip())
    return None


def _urn_from_read_item(item: dict[str, Any]) -> str | None:
    urn = item.get("urn")
    if isinstance(urn, str) and urn.strip():
        return urn.strip()
    post_url = item.get("post_url")
    if isinstance(post_url, str):
        m = re.search(r"urn:li:(activity|ugcPost):(\d+)", post_url)
        if m:
            return f"urn:li:{m.group(1)}:{m.group(2)}"
    return None


def _post_key(post: Post) -> str:
    # Canonicalize across sources:
    # the same feed item may be observed once with `urn` and later only with `post_url`.
    # If both contain the activity id, use it as a stable dedupe key.
    if (urn_s := (post.urn or "").strip()) and (m := _ACTIVITY_RE.search(urn_s)):
        return f"activity:{m.group(1)}"

    if (url_s := (post.post_url or "").strip()) and (m := _ACTIVITY_RE.search(url_s)):
        return f"activity:{m.group(1)}"

    if post.id:
        return f"id:{post.id}"
    if post.post_url:
        with suppress(Exception):
            pu = urlparse(post.post_url)
            if pu.scheme and pu.netloc:
                norm = f"{pu.scheme}://{pu.netloc}{pu.path}".lower().rstrip("/")
                return f"url:{norm}"
        return f"url:{post.post_url}"

    author = post.author.name if post.author else ""
    published = post.published_at_text or ""
    content = (post.content or "").replace("\n", " ").strip()
    if len(content) > 120:
        content = content[:120]
    return f"fallback:{author}|{published}|{content}"


def _urn_from_post_url(post_url: str | None) -> str | None:
    if not isinstance(post_url, str) or not post_url.strip():
        return None
    m = re.search(r"urn:li:(activity|ugcPost):(\d+)", post_url)
    if m:
        return f"urn:li:{m.group(1)}:{m.group(2)}"
    return None


def _enrich_post(existing: Post, incoming: Post) -> Post:
    urn = existing.urn or incoming.urn
    if not urn:
        urn = _urn_from_post_url(existing.post_url) or _urn_from_post_url(incoming.post_url)

    post_url = existing.post_url or incoming.post_url
    if not post_url and urn:
        post_url = f"https://www.linkedin.com/feed/update/{urn}"

    return Post(
        id=existing.id or incoming.id,
        urn=urn,
        post_url=post_url,
        author=merge_authors(existing.author, incoming.author),
        content=existing.content or incoming.content,
        published_at_text=existing.published_at_text or incoming.published_at_text,
        reactions_count=(
            existing.reactions_count
            if existing.reactions_count is not None
            else incoming.reactions_count
        ),
        comments_count=(
            existing.comments_count
            if existing.comments_count is not None
            else incoming.comments_count
        ),
        media_urls=existing.media_urls or incoming.media_urls,
    )


def _upsert_post(results: list[Post], seen: set[str], post: Post) -> bool:
    """Insert or enrich an existing post keyed by `_post_key`. Returns True if inserted."""
    key = _post_key(post)
    if not key:
        return False

    for idx, existing in enumerate(results):
        if _post_key(existing) != key:
            continue
        enriched = _enrich_post(existing, post)
        results[idx] = enriched
        # region agent log
        agent_dbg_log(
            run_id="post-fix",
            hypothesis_id="H6",
            location="client.py:_upsert_post",
            message="Enriched existing post from secondary source",
            data={
                "has_author": enriched.author is not None,
                "has_headline": bool(enriched.author and enriched.author.headline),
                "has_profile_url": bool(enriched.author and enriched.author.profile_url),
                "has_post_urn": bool(enriched.urn),
            },
        )
        # endregion
        return False

    seen.add(key)
    results.append(post)
    return True


class LinkedInClient:
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
        - auth/cookies: инъекция и извлечение cookies (без хранения).
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
        - auth/cookies: cookie injection and extraction (no persistence).
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
        cookies: Cookies | None = None,
        config: LinkedInClientConfig | None = None,
        headless: bool = True,
        timeout_ms: int = 30_000,
        slow_mo_ms: int | None = None,
    ) -> None:
        self._initial_cookies = cookies
        if config is None:
            browser_cfg = BrowserConfig(
                headless=headless, timeout_ms=timeout_ms, slow_mo_ms=slow_mo_ms
            )
            self._client_cfg = LinkedInClientConfig(browser=browser_cfg)
        else:
            self._client_cfg = config

        self._browser = BrowserManager(self._client_cfg.browser)

        self._entered = False
        self._login_page_opened = False
        self._manual_login_completed = False

    def __enter__(self) -> LinkedInClient:
        if self._entered:
            raise BrowserLifecycleError("LinkedInClient cannot be re-entered.")
        self._entered = True

        handle = self._browser.start()
        if self._initial_cookies:
            inject_cookies(handle.context, self._initial_cookies)
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

    def login_and_get_cookies(
        self,
        *,
        method: LoginMethod = LoginMethod.email,
        identifier: str | None = None,
        password: str | None = None,
        cancelled: Callable[[], bool] | None = None,
        on_checkpoint: Callable[[], None] | None = None,
    ) -> list[dict]:
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
        if self._initial_cookies:
            raise LinkedInClientError(
                "Cookies were provided; manual login is not supported in this mode."
            )
        if self._manual_login_completed:
            return extract_cookies(self._browser.handle.context)

        # Ensure we're on the LinkedIn login page before starting a UI flow.
        with suppress(Exception):
            self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        timeout_ms = self._client_cfg.browser.timeout_ms
        ctx = self._browser.handle.context

        if method == LoginMethod.email:
            flow = EmailPasswordLoginFlow(
                timeout_ms=timeout_ms,
                params=EmailPasswordLoginParams(identifier=identifier, password=password),
                cancelled=cancelled,
                on_checkpoint=on_checkpoint,
            )
            flow.run(page=self.page, context=ctx)
        elif method in (LoginMethod.google, LoginMethod.apple):
            flow = SocialLoginFlow(
                timeout_ms=timeout_ms,
                params=SocialLoginParams(method=method),
                cancelled=cancelled,
                on_checkpoint=on_checkpoint,
            )
            flow.run(page=self.page, context=ctx)
        else:
            raise LinkedInClientError(f"Unsupported login method: {method!r}")

        self._manual_login_completed = True
        return extract_cookies(ctx)

    def get_cookies(self) -> list[dict]:
        """
        RU: Снимок текущих cookies контекста (boundary state export).
            Библиотека не хранит cookies — вызывающая сторона решает, где и как их персистить.

        EN: Snapshot current context cookies (boundary state export).
            The library does not persist cookies; the caller decides where/how to store them.
        """
        if not self._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        return extract_cookies(self._browser.handle.context)

    def read_posts(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """
        RU: Прочитать посты из текущей страницы feed (без скролла).
            Скроллинг/дозагрузка выполняются другими модулями. Этот метод только читает DOM.

        EN: Read posts from the current feed page (no scrolling).
            Scrolling/loading is handled elsewhere. This method only reads from the DOM.
        """
        if not self._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        if limit <= 0:
            return []

        from .parsing.read_posts import read_posts as _read_posts

        raw = _read_posts(self.page, limit)
        return [
            {
                "author": item.get("author"),
                "created_at": item.get("created_at"),
                "text": item.get("text"),
                "post_url": item.get("post_url"),
                "urn": item.get("urn"),
            }
            for item in raw
        ]

    def fetch_posts(self, *, limit: int = 10) -> list[Post]:
        """
        RU: Высокоуровневая операция “получить посты из ленты”.
            Оркестрирует навигацию/ожидания/скролл/парсинг и возвращает доменные `Post`.

        EN: High-level “fetch feed posts” operation.
            Orchestrates navigation/waiting/scrolling/parsing and returns domain `Post` objects.
        """
        if not self._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        if limit <= 0:
            return []

        navigator = FeedNavigator(feed_url=self._client_cfg.feed_url)
        waiter = FeedWaiter(timeout_ms=self._client_cfg.browser.timeout_ms)
        scroller = HumanScroller(config=self._client_cfg.scroll)
        parser = PostParser(
            expand_truncated_text=self._client_cfg.expand_truncated_text
        )

        for attempt in range(2):
            try:
                navigator.goto_feed(self.page)
                waiter.wait_for_feed_ready(self.page)

                seen: set[str] = set()
                results: list[Post] = []

                def merge(posts: list[Post]) -> None:
                    for p in posts:
                        content = (p.content or "").strip()
                        if not content:
                            continue
                        _upsert_post(results, seen, p)

                def merge_read_posts(raw_posts: list[dict[str, Any]]) -> None:
                    for item in raw_posts:
                        created_at = item.get("created_at")
                        text = item.get("text")
                        post_url = item.get("post_url")
                        author = _author_from_read_item(item)
                        urn = _urn_from_read_item(item)

                        if not isinstance(text, str) or not text.strip():
                            continue

                        # region agent log
                        agent_dbg_log(
                            run_id="post-fix",
                            hypothesis_id="H1",
                            location="client.py:merge_read_posts",
                            message="Creating Author from read_posts item",
                            data={
                                "has_author": author is not None,
                                "has_headline": bool(author and author.headline),
                                "has_profile_url": bool(author and author.profile_url),
                                "has_author_urn": bool(author and author.urn),
                                "has_post_urn": bool(urn),
                                "item_keys": sorted(item.keys()),
                            },
                        )
                        # endregion

                        p = Post(
                            author=author,
                            content=text,
                            published_at_text=created_at,
                            post_url=post_url,
                            urn=urn,
                        )
                        _upsert_post(results, seen, p)

                parse_budget = min(max(limit * 5, 50), 250)

                merge(parser.parse_posts(self.page, limit=parse_budget))
                merge_read_posts(
                    self.read_posts(limit=min(parse_budget, limit * 2))
                )

                if len(results) >= limit:
                    return results[:limit]

                no_progress = 0
                for i in range(self._client_cfg.scroll.max_scrolls):
                    before_len = len(results)
                    scrolled = scroller.scroll_batch(page=self.page)

                    # EN/RU: Small settle window for lazy-load to attach.
                    with suppress(Exception):
                        self.page.wait_for_load_state("networkidle", timeout=1500)
                    self.page.wait_for_timeout(250)

                    merge(parser.parse_posts(self.page, limit=parse_budget))
                    merge_read_posts(
                        self.read_posts(limit=min(parse_budget, limit * 2))
                    )

                    if len(results) >= limit:
                        return results[:limit]

                    got_new = len(results) > before_len
                    if scrolled or got_new:
                        no_progress = 0
                    else:
                        no_progress += 1
                        if (
                            no_progress
                            >= self._client_cfg.scroll.max_no_progress_scrolls
                        ):
                            break

                return results[:limit]
            except FeedLoadError:
                if attempt == 0:
                    self.page.reload(wait_until="domcontentloaded")
                    continue
                raise

    def is_logged_in(self) -> bool:
        if not self._entered:
            return False
        url = self.page.url.lower()
        return (
            "linkedin.com/feed" in url
            and "login" not in url
            and "checkpoint" not in url
        )
