from __future__ import annotations

import re
import urllib.parse
from playwright.sync_api import Locator, Page

# EN/RU: keywords for semantic overflow ("…") menu button inside a single post container.
MENU_BUTTON_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ru": (
        "меню",
        "управ",
        "опц",
        "действ",
        "дополнит",
        "открыть меню",
        "см. дополнительные",
    ),
    "en": (
        "menu",
        "more",
        "action",
        "options",
        "control",
        "overflow",
        "open menu",
    ),
}

# EN/RU: keywords for "Copy link to post" menu item (overlay, page-scoped).
COPY_LINK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ru": (
        "скопировать ссылку",
        "копировать ссылку",
        "ссылк",
        "копир",
    ),
    "en": (
        "copy link",
        "copy post link",
        "link to post",
        "copy url",
    ),
}

_URN_RE = re.compile(r"urn:li:(activity|ugcPost):(\d+)")
_URN_ENC_RE = re.compile(r"urn%3Ali%3A(activity|ugcPost)%3A(\d+)", re.IGNORECASE)


def _make_absolute(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("/"):
        return f"https://www.linkedin.com{href}"
    if href.startswith("http"):
        return href
    return f"https://www.linkedin.com/{href}"


def _urn_from_any(raw: str) -> tuple[str, str] | None:
    s = (raw or "").strip()
    if not s:
        return None
    decoded = urllib.parse.unquote(s)
    for cand in (s, decoded):
        m = _URN_RE.search(cand)
        if m:
            return m.group(1), m.group(2)
        m2 = _URN_ENC_RE.search(cand)
        if m2:
            return m2.group(1), m2.group(2)
    return None


def _build_post_url(urn_type: str, urn_id: str) -> str:
    return f"https://www.linkedin.com/feed/update/urn:li:{urn_type}:{urn_id}"


def _looks_like_post_url(url: str) -> bool:
    """
    Validate that extracted URL looks like a post permalink, not a profile/company listing.
    """
    u = (url or "").strip()
    if not u or "linkedin.com" not in u:
        return False
    low = u.lower()
    if any(x in low for x in ("/in/", "/company/", "/school/")):
        return False
    return any(x in low for x in ("/feed/update/", "/posts/", "/activity-"))


def _is_listing_posts_url(url: str) -> bool:
    """
    Reject known non-permalink /posts/ listing pages.
    Observed wrong examples: https://www.linkedin.com/company/<x>/posts/
    """
    try:
        path = (urllib.parse.urlparse(url).path or "").lower()
    except Exception:
        path = ""
    if re.fullmatch(r"/(company|in|school)/[^/]+/posts/?", path or ""):
        return True
    if re.fullmatch(r"/posts/[^/]+/?", path or ""):
        return True
    return False


def find_overflow_menu_button(post_container: Locator) -> Locator | None:
    """
    Step 1: Find the "..." overflow menu button strictly inside the given post container.
    Best-effort semantic search (no page-wide queries).
    """
    keywords = MENU_BUTTON_KEYWORDS.get("ru", ()) + MENU_BUTTON_KEYWORDS.get("en", ())

    # Some controls appear only on hover.
    try:
        post_container.hover(timeout=800)
    except Exception:
        pass

    candidates: list[Locator] = []
    try:
        for sel in ("button[aria-haspopup='menu']", "button[aria-haspopup='true']"):
            loc = post_container.locator(sel)
            n = min(loc.count(), 20)
            for i in range(n):
                candidates.append(loc.nth(i))
    except Exception:
        pass

    if not candidates:
        try:
            btns = post_container.locator("button")
            n = min(btns.count(), 40)
            for i in range(n):
                candidates.append(btns.nth(i))
        except Exception:
            candidates = []

    best: Locator | None = None
    best_score = -1.0

    for btn in candidates:
        score = 0.0

        try:
            aria_hm = (btn.get_attribute("aria-haspopup") or "").lower()
            if aria_hm in ("true", "menu"):
                score += 10.0
        except Exception:
            pass

        try:
            aria_label = (btn.get_attribute("aria-label") or "").lower()
            if any(k in aria_label for k in keywords):
                score += 6.0
        except Exception:
            pass

        for attr in ("data-testid", "data-control-name", "data-control-id"):
            try:
                v = (btn.get_attribute(attr) or "").lower()
                if any(k in v for k in ("menu", "more", "action", "options", "overflow")):
                    score += 3.0
                    break
            except Exception:
                continue

        try:
            t = (btn.inner_text(timeout=200) or "")
            if "..." in t or "…" in t:
                score += 1.0
        except Exception:
            pass

        # Best-effort: prioritize right side (menu is usually top-right).
        try:
            box = btn.bounding_box()
            if box and box.get("x") is not None:
                score += float(box["x"]) / 10000.0
        except Exception:
            pass

        if score > best_score:
            best_score = score
            best = btn

    return best


def open_overflow_menu(menu_button: Locator) -> Locator | None:
    """
    Step 2: Click overflow menu button and wait for overlay to attach.
    """
    page = menu_button.page
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    try:
        menu_button.click(timeout=1500)
    except Exception:
        return None

    try:
        page.locator("[role='menu']:visible").first.wait_for(state="visible", timeout=2000)
    except Exception:
        return None

    menu = page.locator("[role='menu']:visible").last
    try:
        menu.locator("[role='menuitem']").first.wait_for(state="visible", timeout=1500)
    except Exception:
        return None
    return menu


def _find_copy_link_menu_item_semantic(menu: Locator) -> Locator | None:
    """
    Semantic search among current [role=menuitem] on the page (overlay).
    """
    ru = COPY_LINK_KEYWORDS.get("ru", ())
    en = COPY_LINK_KEYWORDS.get("en", ())

    try:
        items = menu.locator("[role='menuitem']")
        n = min(items.count(), 80)
    except Exception:
        return None

    best: Locator | None = None
    best_score = -1.0

    for i in range(n):
        it = items.nth(i)
        score = 0.0

        for attr in ("data-testid", "aria-label"):
            try:
                v = (it.get_attribute(attr) or "").lower()
                if any(k in v for k in ("copy", "link", "share-url", "share url")):
                    score += 4.0
                if any(k in v for k in ("копир", "ссылк")):
                    score += 4.0
            except Exception:
                continue

        try:
            text = (it.inner_text(timeout=300) or "")
            tl = " ".join(text.split()).lower()
            # LinkedIn sometimes renders icon-only items; keep only if we already have strong attrs.
            if not tl:
                if score < 4.0:
                    continue
            else:
                if any(k in tl for k in en) or any(k in tl for k in ru):
                    score += 6.0
                if any(k in tl for k in ("link", "ссылк")):
                    score += 6.0
                if "скопировать ссылку" in tl or "copy link" in tl:
                    score += 2.0
        except Exception:
            continue

        if score > 0.0:
            try:
                text2 = (it.inner_text(timeout=200) or "").lower()
                if any(w in text2 for w in ("удал", "delete", "report", "жалоб", "скрыть", "hide")):
                    score -= 10.0
            except Exception:
                pass

        if score > best_score:
            best_score = score
            best = it

    if best is not None and best_score >= 8.0:
        return best
    return None


def click_copy_link_menu_item(menu: Locator) -> Locator | None:
    """
    Step 3: Find and click menu item "Copy link ..." (semantic + selector fallbacks).
    Returns the clicked locator when possible.
    """
    item = _find_copy_link_menu_item_semantic(menu)
    method = "semantic_menuitem" if item is not None else ""

    if item is None:
        copy_link_selectors = [
            'button[aria-label*="копирова"]',
            'button[aria-label*="copy link"]',
            'button:has-text("Копировать ссылку")',
            'button:has-text("Copy link")',
            'button:has-text("Скопировать ссылку")',
            'button:has-text("Скопировать ссылку публикации")',
            'button:has-text("Скопировать ссылку на публикацию")',
            "div[data-test-share-article]",
            'li:has-text("Копировать ссылку")',
        ]
        for sel in copy_link_selectors:
            loc = menu.locator(sel).first
            try:
                if loc.count() > 0:
                    item = loc
                    method = f"selector:{sel}"
                    break
            except Exception:
                continue

    if item is None:
        return None
    try:
        if item.count() > 0:
            item.click(timeout=1500)
    except Exception:
        return None
    return item


def read_post_url_after_copy(page: Page, *, clicked_item: Locator | None = None) -> str | None:
    """
    Step 4: Read URL after clicking 'Copy link ...' (attributes first, then modal/input).
    """
    # A) Try attributes (no modal, no clipboard)
    if clicked_item is not None:
        for attr in ("data-share-url", "data-test-share-url"):
            try:
                raw = clicked_item.get_attribute(attr) if clicked_item.count() > 0 else None
            except Exception:
                raw = None
            if raw and "linkedin.com" in raw:
                url = _make_absolute(raw)
                if _looks_like_post_url(url) and not _is_listing_posts_url(url):
                    return url

    # B) Read from share modal/input
    try:
        page.locator(".artdeco-modal").first.wait_for(state="visible", timeout=2000)
    except Exception:
        pass

    url_selectors = (
        "input[readonly][value*='linkedin.com']",
        "input[data-test-share-url]",
        ".share-box-feed-entry__copyable-input",
        ".artdeco-modal__content input[readonly]",
        "input[aria-label*='ссылка']",
        "input[aria-label*='link']",
    )
    for sel in url_selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() > 0:
                loc.wait_for(state="visible", timeout=800)
                val = loc.get_attribute("value")
                if val and "linkedin.com" in val:
                    url = _make_absolute(val)
                    if _looks_like_post_url(url) and not _is_listing_posts_url(url):
                        return url
        except Exception:
            continue
    return None


def close_any_open_menus(page: Page) -> None:
    """
    Best-effort: close open menus/modals.
    """
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    try:
        page.locator("[role='menu']:visible").first.wait_for(state="hidden", timeout=800)
    except Exception:
        pass
    try:
        page.mouse.click(10, 10)
    except Exception:
        pass


def extract_post_url_from_dom(container: Locator) -> str | None:
    """
    Optional fast-path: extract canonical post url using tracking attrs + href scan.
    """
    attrs = ("data-view-tracking-scope", "data-tracking-scope", "data-urn", "data-id")

    # 0) Container tracking attributes
    for attr in attrs:
        try:
            raw = container.get_attribute(attr)
        except Exception:
            raw = None
        urn = _urn_from_any(raw or "")
        if urn:
            return _build_post_url(urn[0], urn[1])

    # 1) Descendant tracking attributes (bounded)
    for attr in attrs:
        try:
            nodes = container.locator(f"*[{attr}]")
            n = nodes.count()
        except Exception:
            n = 0
        for i in range(min(n, 80)):
            try:
                raw = nodes.nth(i).get_attribute(attr)
            except Exception:
                continue
            urn = _urn_from_any(raw or "")
            if urn:
                return _build_post_url(urn[0], urn[1])

    # 2) href scan
    try:
        hrefs = container.locator("a[href]").evaluate_all(
            "els => els.map(a => a.getAttribute('href')).filter(Boolean)"
        )
    except Exception:
        hrefs = []

    candidates: list[str] = []
    posts_candidates: list[str] = []
    for href in hrefs[:250]:
        h = str(href)
        urn = _urn_from_any(h)
        if urn:
            candidates.append(_build_post_url(urn[0], urn[1]))
            continue

        decoded = urllib.parse.unquote(h).split("#", 1)[0].split("?", 1)[0]
        abs_url = _make_absolute(decoded)
        if "/feed/update/" in abs_url or "/activity-" in abs_url:
            candidates.append(abs_url)
            continue
        if "/posts/" in abs_url:
            if _is_listing_posts_url(abs_url):
                continue
            posts_candidates.append(abs_url)

    if candidates:
        candidates.sort(key=lambda u: (0 if "/feed/update/" in u else 1, len(u)))
        return candidates[0]
    if posts_candidates:
        # Prefer longer/more specific posts URLs.
        posts_candidates.sort(key=lambda u: len(u))
        return posts_candidates[0]
    return None


def get_post_url(container: Locator) -> str | None:
    """
    Public helper: prefer menu-based copy-link flow (source of truth).
    Falls back to DOM-based extraction if UI flow fails.
    """
    page = container.page

    # First pass: deterministic DOM extraction has fewer side-effects than UI menu flow.
    # This significantly reduces flaky behavior on dynamic LinkedIn overlays.
    dom_url = extract_post_url_from_dom(container)
    if dom_url and _looks_like_post_url(dom_url) and not _is_listing_posts_url(dom_url):
        return dom_url

    btn = find_overflow_menu_button(container)
    if btn is None:
        wider = container.locator("xpath=ancestor::*[@role='listitem'][1]").first
        try:
            if wider.count() > 0:
                btn = find_overflow_menu_button(wider)
        except Exception:
            pass

    menu = open_overflow_menu(btn) if btn is not None else None
    if menu is not None:
        clicked = click_copy_link_menu_item(menu)
        page.wait_for_timeout(250)
        url = read_post_url_after_copy(page, clicked_item=clicked)
        close_any_open_menus(page)
        if url:
            return url

    close_any_open_menus(page)
    return None

