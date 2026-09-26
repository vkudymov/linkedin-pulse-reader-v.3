from __future__ import annotations

import logging
import re
from contextlib import suppress
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page

from linkedin_search_core.exceptions import BrowserLifecycleError, FeedLoadError
from linkedin_search_core.session import LinkedInSession
from linkedin_search_core.loading.scroller import HumanScroller
from linkedin_search_posts.loading.waiter import FeedWaiter
from linkedin_search_posts.models.post import Author, Post, merge_authors
from linkedin_search_posts.navigation.feed import FeedNavigator
from linkedin_search_posts.parsing.post_parser import PostParser

_log = logging.getLogger(__name__)
_ACTIVITY_RE = re.compile(r"urn:li:activity:(\d+)")


def _feed_dom_counts(page: Page) -> dict[str, int]:
    selectors = {
        "text_boxes": "[data-testid='expandable-text-box']",
        "post_containers": (
            "div.feed-shared-update-v2, div.occludable-update, article[data-urn]"
        ),
    }
    out: dict[str, int] = {}
    for key, sel in selectors.items():
        try:
            out[key] = page.locator(sel).count()
        except Exception:
            out[key] = -1
    return out


def _optional_stripped(value: Any) -> str | None:
    return (value.strip() or None) if isinstance(value, str) else None


def _author_from_dict(raw: dict[str, Any]) -> Author | None:
    name = _optional_stripped(raw.get("name"))
    if name is None:
        return None
    return Author(
        name=name,
        headline=_optional_stripped(raw.get("headline")),
        profile_url=_optional_stripped(raw.get("profile_url")),
        urn=_optional_stripped(raw.get("urn")),
        avatar_url=_optional_stripped(raw.get("avatar_url")),
    )


def _author_from_read_item(item: dict[str, Any]) -> Author | None:
    raw = item.get("author")
    if isinstance(raw, dict):
        return _author_from_dict(raw)
    name = _optional_stripped(raw)
    return Author(name=name) if name else None


def _urn_from_read_item(item: dict[str, Any]) -> str | None:
    if urn := _optional_stripped(item.get("urn")):
        return urn
    post_url = item.get("post_url")
    if isinstance(post_url, str) and (m := re.search(r"urn:li:(activity|ugcPost):(\d+)", post_url)):
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
    return f"urn:li:{m.group(1)}:{m.group(2)}" if m else None


def _enrich_post(existing: Post, incoming: Post) -> Post:
    urn = (
        existing.urn
        or incoming.urn
        or _urn_from_post_url(existing.post_url)
        or _urn_from_post_url(incoming.post_url)
    )

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


def _upsert_post(results: list[Post], post: Post) -> bool:
    """Insert or enrich an existing post keyed by `_post_key`. Returns True if inserted."""
    key = _post_key(post)
    if not key:
        return False

    for idx, existing in enumerate(results):
        if _post_key(existing) != key:
            continue
        enriched = _enrich_post(existing, post)
        results[idx] = enriched
        return False

    results.append(post)
    return True


class PostSearch:
    """Collect LinkedIn feed posts from an open LinkedInSession."""

    def __init__(self, session: LinkedInSession) -> None:
        self._session = session

    def read(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """
        RU: Прочитать посты из текущей страницы feed (без скролла).
            Скроллинг/дозагрузка выполняются другими модулями. Этот метод только читает DOM.

        EN: Read posts from the current feed page (no scrolling).
            Scrolling/loading is handled elsewhere. This method only reads from the DOM.
        """
        session = self._session
        if not session._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        if limit <= 0:
            return []

        from .parsing.read_posts import read_posts as _read_posts

        raw = _read_posts(session.page, limit)
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

    def fetch(self, *, limit: int = 10) -> list[Post]:
        """
        RU: Высокоуровневая операция “получить посты из ленты”.
            Оркестрирует навигацию/ожидания/скролл/парсинг и возвращает доменные `Post`.

        EN: High-level “fetch feed posts” operation.
            Orchestrates navigation/waiting/scrolling/parsing and returns domain `Post` objects.
        """
        session = self._session
        if not session._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        if limit <= 0:
            return []

        navigator = FeedNavigator(feed_url=session._client_cfg.feed_url)
        waiter = FeedWaiter(timeout_ms=session._client_cfg.browser.timeout_ms)
        scroller = HumanScroller(config=session._client_cfg.scroll)
        parser = PostParser(
            expand_truncated_text=session._client_cfg.expand_truncated_text
        )

        for attempt in range(2):
            try:
                navigator.goto_feed(session.page)
                waiter.wait_for_feed_ready(session.page)

                results: list[Post] = []

                def merge(posts: list[Post]) -> None:
                    for p in posts:
                        content = (p.content or "").strip()
                        if not content:
                            continue
                        _upsert_post(results, p)

                def merge_read_posts(raw_posts: list[dict[str, Any]]) -> None:
                    for item in raw_posts:
                        created_at = item.get("created_at")
                        text = item.get("text")
                        post_url = item.get("post_url")
                        author = _author_from_read_item(item)
                        urn = _urn_from_read_item(item)

                        if not isinstance(text, str) or not text.strip():
                            continue

                        p = Post(
                            author=author,
                            content=text,
                            published_at_text=created_at,
                            post_url=post_url,
                            urn=urn,
                        )
                        _upsert_post(results, p)

                parse_budget = min(max(limit * 5, 50), 250)
                read_limit = min(parse_budget, limit * 2)

                merge(parser.parse_posts(session.page, limit=parse_budget))
                merge_read_posts(self.read(limit=read_limit))

                _log.info(
                    "Feed initial parse: %s/%s posts (DOM text_boxes=%s)",
                    len(results),
                    limit,
                    _feed_dom_counts(session.page).get("text_boxes", "?"),
                )

                if len(results) >= limit:
                    return results[:limit]

                no_progress = 0
                max_scrolls = session._client_cfg.scroll.max_scrolls
                for i in range(max_scrolls):
                    before_len = len(results)
                    scrolled = scroller.scroll_batch(page=session.page)

                    # EN/RU: Small settle window for lazy-load to attach.
                    with suppress(Exception):
                        session.page.wait_for_load_state("networkidle", timeout=1500)
                    session.page.wait_for_timeout(250)

                    merge(parser.parse_posts(session.page, limit=parse_budget))
                    merge_read_posts(self.read(limit=read_limit))

                    _log.info(
                        "Feed scroll %s/%s: %s/%s posts (scrolled=%s)",
                        i + 1,
                        max_scrolls,
                        len(results),
                        limit,
                        scrolled,
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
                            >= session._client_cfg.scroll.max_no_progress_scrolls
                        ):
                            break

                _log.info(
                    "Feed fetch finished: collected %s posts (requested %s)",
                    len(results),
                    limit,
                )
                return results[:limit]
            except FeedLoadError:
                if attempt == 0:
                    session.page.reload(wait_until="domcontentloaded")
                    continue
                raise
        # Unreachable: loop either returns results or raises.
        return []

    def search(self, *, limit: int = 10) -> list[Post]:
        """Alias of fetch()."""
        return self.fetch(limit=limit)
