from __future__ import annotations

"""
RU: Парсинг DOM -> доменные модели.
    Здесь сосредоточены селекторы и эвристики (наиболее “хрупкий” слой). Остальная система должна
    оставаться проще: навигация/ожидания/скролл только обеспечивают наличие контента.

EN: DOM -> domain parsing.
    This is where selectors and heuristics live (the most fragile layer). The rest of the system stays
    simpler: navigation/waiting/scrolling only ensure content is present.
"""

import re
from dataclasses import dataclass

from playwright.sync_api import Locator, Page

from ..models.post import Author, Post, merge_authors
from .author_extract import extract_author_fields, pick_post_container
from .post_url import get_post_url


_POST_CONTAINER_SELECTOR_GROUP = (
    "div.feed-shared-update-v2, "
    "div.occludable-update, "
    "article[data-urn], "
    "div[data-urn], "
    "div[data-id], "
    "div[data-urn*='urn:li:activity'], "
    "div[data-urn*='urn:li:ugcPost'], "
    "div[data-urn*='urn:li:share']"
)
_TEXT_BOX_SELECTOR = "[data-testid='expandable-text-box']"


_COMPACT_RE = re.compile(r"^\s*(?P<num>\d+(?:[.,]\d+)?)\s*(?P<sfx>[KMB])?\s*$", re.IGNORECASE)
_ACTIVITY_URN_RE = re.compile(r"^urn:li:(activity|ugcPost):(\d+)$")


def parse_compact_number(text: str) -> int | None:
    """
    RU: Утилита парсинга UI-чисел (best-effort).
        LinkedIn часто отображает счётчики в компактном виде (например, 1.2K). Ошибки парсинга
        не должны ломать весь результат, поэтому функция возвращает None при неудаче.

    EN: Best-effort parser for UI numbers.
        LinkedIn often renders counters in compact form (e.g., 1.2K). Parsing failures should not break
        the overall result, so the function returns None when parsing is not possible.
    """
    cleaned = (
        text.replace("\u00a0", " ")
        .replace(",", "")
        .replace(" ", "")
        .strip()
    )
    if not cleaned:
        return None
    m = _COMPACT_RE.match(cleaned)
    if not m:
        digits = re.sub(r"[^\d]", "", cleaned)
        return int(digits) if digits else None

    num = float(m.group("num").replace(",", "."))
    sfx = (m.group("sfx") or "").upper()
    mult = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[sfx]
    return int(num * mult)


@dataclass(frozen=True, slots=True)
class PostParser:
    """
    RU: Преобразователь DOM-элементов ленты в `Post`.
        Best-effort по дизайну: ошибки изолируются на уровне отдельных постов.

    EN: Converts feed DOM elements into `Post`.
        Best-effort by design: failures are isolated per post.
    """
    expand_truncated_text: bool = True

    def parse_posts(self, page: Page, limit: int) -> list[Post]:
        if limit <= 0:
            return []

        containers = page.locator(_POST_CONTAINER_SELECTOR_GROUP)
        count = containers.count()
        use_text_boxes = count <= 0
        if use_text_boxes:
            containers = page.locator(_TEXT_BOX_SELECTOR)
            count = containers.count()

        results: list[Post] = []
        seen: set[str] = set()

        for i in range(min(count, limit * 3)):
            if len(results) >= limit:
                break
            raw = containers.nth(i)
            container = pick_post_container(raw) if use_text_boxes else raw
            try:
                post = self._parse_container(container)
            except Exception:  # noqa: BLE001 - isolate per-post failures
                continue

            key = post.urn or post.id
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            results.append(post)

        return results[:limit]

    def _parse_container(self, container: Locator) -> Post:
        # LinkedIn feed DOM is nested; we often start from an inner node (e.g. text block)
        # that doesn't contain ids or the overflow menu. Try to upgrade to a stable ancestor.
        container_used = container
        upgrade_by: str | None = None
        try:
            has_ids = bool((container.get_attribute("data-urn") or "").strip()) or bool(
                (container.get_attribute("data-id") or "").strip()
            )
        except Exception:
            has_ids = False

        if not has_ids:
            candidates = (
                "xpath=ancestor::*[@data-urn][1]",
                "xpath=ancestor::*[@data-id][1]",
                "xpath=ancestor::*[@role='article'][1]",
                "xpath=ancestor::*[@role='listitem'][1]",
                "xpath=ancestor::div[contains(@class,'feed-shared-update-v2')][1]",
                "xpath=ancestor::div[contains(@class,'occludable-update')][1]",
            )
            for sel in candidates:
                loc = container.locator(sel).first
                try:
                    if loc.count() > 0:
                        container_used = loc
                        upgrade_by = sel
                        break
                except Exception:
                    continue

        if self.expand_truncated_text:
            self._try_expand(container_used)

        urn = _first_non_empty(
            container_used.get_attribute("data-urn"),
            container_used.get_attribute("data-id"),
        )
        # Filter out non-post cards (e.g. aggregates) early.
        if urn and isinstance(urn, str) and "urn:li:aggregate:" in urn:
            raise ValueError("Non-post aggregate container")

        post_url = self._try_get_post_url(container_used)

        author = self._try_get_author(container_used)
        tb = container_used.locator("[data-testid='expandable-text-box']").first
        try:
            if tb.count() > 0:
                upgraded = pick_post_container(tb)
                upgraded_author = self._try_get_author(upgraded)
                author = merge_authors(author, upgraded_author)
                if upgraded_author is not None:
                    container_used = upgraded
        except Exception:
            pass

        content = self._try_get_content(container_used)
        published_at_text = self._try_get_published_text(container_used)

        reactions = self._try_get_reactions_count(container_used)
        comments = self._try_get_comments_count(container_used)
        media_urls = tuple(self._try_get_media_urls(container_used))

        # Canonicalize: fill missing urn from URL and vice-versa.
        if not urn and post_url:
            m = re.search(r"urn:li:(activity|ugcPost):(\d+)", post_url)
            if m:
                urn = f"urn:li:{m.group(1)}:{m.group(2)}"
        if urn and not post_url:
            m = _ACTIVITY_URN_RE.match(str(urn).strip())
            if m:
                post_url = f"https://www.linkedin.com/feed/update/{str(urn).strip()}"

        return Post(
            urn=urn,
            post_url=post_url,
            author=author,
            content=content,
            published_at_text=published_at_text,
            reactions_count=reactions,
            comments_count=comments,
            media_urls=media_urls,
        )

    def _try_expand(self, container: Locator) -> None:
        # Known LinkedIn "see more" button class in many variants.
        btn = container.locator("button.feed-shared-inline-show-more-text__see-more-less-toggle").first
        try:
            if btn.count() > 0:
                btn.click(timeout=500)
        except Exception:
            return

    def _try_get_post_url(self, container: Locator) -> str | None:
        # Source of truth: UI flow “… → Copy link … → read URL”.
        url = get_post_url(container)
        if url:
            return url
        return None

    def _try_get_author(self, container: Locator) -> Author | None:
        fields = extract_author_fields(container)
        name = fields.get("name")
        if not isinstance(name, str) or not name.strip():
            return None

        headline_val = fields.get("headline")
        profile_val = fields.get("profile_url")
        urn_val = fields.get("urn")
        avatar_val = fields.get("avatar_url")
        author = Author(
            name=name,
            headline=headline_val if isinstance(headline_val, str) else None,
            profile_url=profile_val if isinstance(profile_val, str) else None,
            urn=urn_val if isinstance(urn_val, str) else None,
            avatar_url=avatar_val if isinstance(avatar_val, str) else None,
        )
        return author

    def _try_get_content(self, container: Locator) -> str | None:
        return _first_text(
            container,
            [
                "[data-testid='expandable-text-box']",
                "div.feed-shared-update-v2__description",
                "div.update-components-text",
                "span.break-words",
            ],
        )

    def _try_get_published_text(self, container: Locator) -> str | None:
        return _first_text(
            container,
            [
                "span.update-components-actor__sub-description",
                "span.feed-shared-actor__sub-description",
                "time",
            ],
        )

    def _try_get_reactions_count(self, container: Locator) -> int | None:
        txt = _first_text(
            container,
            [
                "span.social-details-social-counts__reactions-count",
                "li.social-details-social-counts__reactions span",
            ],
        )
        return parse_compact_number(txt) if txt else None

    def _try_get_comments_count(self, container: Locator) -> int | None:
        # Often 'X comments' is in a button or span; this is best-effort.
        txt = _first_text(
            container,
            [
                "span.social-details-social-counts__comments",
                "button[aria-label*='comment'] span",
            ],
        )
        return parse_compact_number(txt) if txt else None

    def _try_get_media_urls(self, container: Locator) -> list[str]:
        urls: list[str] = []
        try:
            imgs = container.locator("img").all()
            for img in imgs:
                src = img.get_attribute("src")
                if src and ("media" in src or "dms" in src):
                    urls.append(src)
        except Exception:
            pass

        try:
            sources = container.locator("video source").all()
            for s in sources:
                src = s.get_attribute("src")
                if src:
                    urls.append(src)
        except Exception:
            pass

        # Dedupe but keep order.
        seen: set[str] = set()
        out: list[str] = []
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            out.append(u)
        return out


def _first_text(container: Locator, selectors: list[str]) -> str | None:
    for sel in selectors:
        loc = container.locator(sel).first
        try:
            if loc.count() > 0:
                txt = loc.inner_text().strip()
                if txt:
                    return txt
        except Exception:
            continue
    return None


def _first_non_empty(*values: str | None) -> str | None:
    for v in values:
        if v:
            vv = v.strip()
            if vv:
                return vv
    return None

