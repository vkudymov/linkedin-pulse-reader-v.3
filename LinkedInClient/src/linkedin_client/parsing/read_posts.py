from __future__ import annotations

"""
RU: Минимальный helper для чтения постов из LinkedIn feed через Playwright Locator API.
    Этот модуль НЕ отвечает за скроллинг/дозагрузку/сохранение — только за извлечение данных из DOM.

EN: Minimal helper to read posts from the LinkedIn feed using Playwright Locator API.
    This module does NOT handle scrolling/loading/persistence — it only extracts data from the DOM.
"""

from typing import Any

from playwright.sync_api import Locator, Page

from .post_url import get_post_url

# Primary anchor (as requested): this is where LinkedIn renders feed post text.
_TEXT_BOX_SELECTOR = "[data-testid='expandable-text-box']"
_EXPAND_TEXT_BUTTON_SELECTOR = "[data-testid='expandable-text-button']"
_TEXT_BLOCK_FALLBACK_SELECTORS: tuple[str, ...] = (
    "div.update-components-text",
    "div.feed-shared-update-v2__description",
)

_AUTHOR_SELECTORS: tuple[str, ...] = (
    "span.update-components-actor__name",
    "span.feed-shared-actor__name",
)
_CREATED_AT_SELECTORS: tuple[str, ...] = (
    "span.update-components-actor__sub-description",
    "span.feed-shared-actor__sub-description",
    "time",
)

_SEE_MORE_SELECTORS: tuple[str, ...] = (
    "button.feed-shared-inline-show-more-text__see-more-less-toggle",
    "button[aria-label*='See more']",
    "button[aria-label*='see more']",
    "button:has-text('…see more')",
    "button:has-text('See more')",
    "button:has-text('see more')",
)


def _maybe_inner_text(locator: Locator) -> str | None:
    try:
        if locator.count() <= 0:
            return None
        txt = locator.first.inner_text()
    except Exception:
        return None

    txt = (txt or "").strip()
    return txt or None


def _wait_for_posts_best_effort(page: Page, *, timeout_ms: int) -> None:
    loc = page.locator(_TEXT_BOX_SELECTOR).first
    try:
        loc.wait_for(state="attached", timeout=timeout_ms)
    except Exception:
        return


def _stabilize_post_count_best_effort(
    page: Page, *, samples: int = 2, pause_ms: int = 250
) -> None:
    if samples <= 1:
        return
    loc = page.locator(_TEXT_BOX_SELECTOR)
    last = None
    stable = 0
    for _ in range(samples * 3):
        try:
            cur = loc.count()
        except Exception:
            return
        if cur == last and cur > 0:
            stable += 1
            if stable >= samples - 1:
                return
        else:
            stable = 0
            last = cur
        page.wait_for_timeout(pause_ms)


def _try_expand_text(container: Locator) -> None:
    # Primary: data-testid expansion button (requested).
    btn = container.locator(_EXPAND_TEXT_BUTTON_SELECTOR).first
    try:
        if btn.count() > 0:
            btn.click(timeout=600)
            return
    except Exception:
        pass

    for sel in _SEE_MORE_SELECTORS:
        btn = container.locator(sel).first
        try:
            if btn.count() > 0:
                btn.click(timeout=600)
                return
        except Exception:
            continue


def _container_key(container: Locator) -> str | None:
    try:
        urn = container.get_attribute("data-urn")
        if urn:
            urn = urn.strip()
            if urn:
                return f"urn:{urn}"
        did = container.get_attribute("data-id")
        if did:
            did = did.strip()
            if did:
                return f"id:{did}"
    except Exception:
        return None
    return None


def _pick_post_container(text_box: Locator) -> Locator:
    """
    Given a text box locator, find the closest post container via XPath ancestors.
    This avoids hard dependency on a single feed container class.
    """
    candidates = (
        "xpath=ancestor::*[@role='article'][1]",
        "xpath=ancestor::*[@role='listitem'][1]",
        "xpath=ancestor::*[@data-urn][1]",
        "xpath=ancestor::*[@data-id][1]",
        "xpath=ancestor::article[@data-urn][1]",
        "xpath=ancestor::div[contains(@class,'feed-shared-update-v2')][1]",
        "xpath=ancestor::div[contains(@class,'occludable-update')][1]",
    )
    for sel in candidates:
        loc = text_box.locator(sel).first
        try:
            if loc.count() > 0:
                return loc
        except Exception:
            continue
    # Last resort: try a generic ancestor div; still allows text extraction from the box itself.
    return text_box.locator("xpath=ancestor::div[1]").first


def _first_text(container: Locator, selectors: tuple[str, ...]) -> str | None:
    for sel in selectors:
        v = _maybe_inner_text(container.locator(sel))
        if v:
            return v
    return None

#
# URL extraction moved to `src/linkedin_client/parsing/post_url.py` (`get_post_url`).


def read_posts(page: Page, limit: int) -> list[dict[str, Any]]:
    """
    Read up to `limit` posts from the currently opened LinkedIn feed page.

    Output format per post:
      {"author": str | None, "created_at": str | None, "text": str | None}

    Notes:
    - Best-effort by design: missing elements do not raise; missing values become None.
    - Does not scroll; assumes content is already loaded by other modules.
    """
    if limit <= 0:
        return []

    _wait_for_posts_best_effort(page, timeout_ms=5000)
    _stabilize_post_count_best_effort(page, samples=2, pause_ms=250)

    selector_used = _TEXT_BOX_SELECTOR
    text_boxes = page.locator(_TEXT_BOX_SELECTOR)
    try:
        total = text_boxes.count()
    except Exception:
        return []

    if total <= 0:
        for sel in _TEXT_BLOCK_FALLBACK_SELECTORS:
            try:
                loc = page.locator(sel)
                c = loc.count()
            except Exception:
                continue
            if c > 0:
                selector_used = sel
                text_boxes = loc
                total = c
                break

    results: list[dict[str, Any]] = []
    max_scan = min(total, max(limit * 5, limit))
    seen: set[str] = set()

    for i in range(max_scan):
        if len(results) >= limit:
            break

        tb = text_boxes.nth(i)
        c = _pick_post_container(tb)

        key = _container_key(c)
        if key and key in seen:
            continue

        # Best-effort: try expanding collapsed text if present.
        _try_expand_text(c)
        author = _first_text(c, _AUTHOR_SELECTORS)
        created_at = _first_text(c, _CREATED_AT_SELECTORS)
        text = _maybe_inner_text(tb)
        # Source of truth: UI flow “… → Copy link … → read URL”.
        # Legacy DOM/href and old menu heuristics are kept below for reference (TODO remove).
        post_url = get_post_url(c)

        # If we don't have an urn/id key, derive a weak fallback key to reduce duplicates
        # caused by DOM re-rendering during reads.
        if not key:
            a = (author or "").strip()
            d = (created_at or "").strip()
            t = (text or "").replace("\n", " ").strip()
            if len(t) > 120:
                t = t[:120]
            if a or d or t:
                key = f"fallback:{a}|{d}|{t}"

        if key and key in seen:
            continue
        if key:
            seen.add(key)
        results.append(
            {
                "author": author,
                "created_at": created_at,
                "text": text,
                "post_url": post_url,
            }
        )

    return results

