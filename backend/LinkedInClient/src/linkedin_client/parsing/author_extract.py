from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

from playwright.sync_api import Locator

from linkedin_client.debug_agent_log import agent_dbg_log

_PROFILE_LINK_SELECTOR = "a[href*='/in/'], a[href*='/company/']"

_LEGACY_NAME_SELECTORS: tuple[str, ...] = (
    "span.update-components-actor__name",
    "span.feed-shared-actor__name",
    "[data-testid='actor-name']",
    "span.update-components-actor__title",
    "a.update-components-actor__meta-link span",
)

_LEGACY_HEADLINE_SELECTORS: tuple[str, ...] = (
    "span.update-components-actor__description",
    "span.feed-shared-actor__description",
    "span.update-components-actor__sub-description",
    "span.feed-shared-actor__sub-description",
)

_HEADLINE_WILDCARD_SELECTORS: tuple[str, ...] = (
    "[data-testid='actor-description']",
    "[class*='update-components-actor'] [class*='description']",
    "[class*='feed-shared-actor'] [class*='description']",
    "div[class*='actor'] span[class*='subtitle']",
)

_URN_ATTRS: tuple[str, ...] = ("data-entity-urn", "data-profile-urn", "data-urn")

_VIEW_PROFILE_RE = re.compile(
    r"^View\s+(.+?)(?:'s|\u2019s)\s+profile$",
    re.IGNORECASE,
)

_TIME_OR_META_RE = re.compile(
    r"^\d+\s*(s|m|h|d|w|mo|yr)\b|\b(edited|promoted|reposted|followers?)\b",
    re.IGNORECASE,
)

_BAD_HREF_TOKENS = ("/posts", "/feed/", "/pulse/", "/search/")


def _maybe_inner_text(locator: Locator) -> str | None:
    try:
        if locator.count() <= 0:
            return None
        txt = locator.first.inner_text()
    except Exception:
        return None
    txt = (txt or "").strip()
    return txt or None


def _profile_link_count(container: Locator) -> int:
    try:
        return container.locator(_PROFILE_LINK_SELECTOR).count()
    except Exception:
        return 0


def pick_post_container(text_box: Locator) -> Locator:
    """
    Find a post container that includes both post text and author header.

    LinkedIn's expandable text box often sits in a nested div; the first structural
    ancestor may not include actor/profile links.
    """
    structural = (
        "xpath=ancestor::*[@role='article'][1]",
        "xpath=ancestor::*[@role='listitem'][1]",
        "xpath=ancestor::*[@data-urn][1]",
        "xpath=ancestor::*[@data-id][1]",
        "xpath=ancestor::article[@data-urn][1]",
        "xpath=ancestor::div[contains(@class,'feed-shared-update-v2')][1]",
        "xpath=ancestor::div[contains(@class,'occludable-update')][1]",
    )

    fallback: Locator | None = None
    for sel in structural:
        loc = text_box.locator(sel).first
        try:
            if loc.count() <= 0:
                continue
            if fallback is None:
                fallback = loc
            if _profile_link_count(loc) > 0:
                return loc
        except Exception:
            continue

    for depth in range(1, 30):
        loc = text_box.locator(f"xpath=ancestor::*[{depth}]").first
        try:
            if loc.count() <= 0:
                break
            if _profile_link_count(loc) > 0:
                return loc
        except Exception:
            break

    if fallback is not None:
        return fallback
    return text_box.locator("xpath=ancestor::div[1]").first


def _looks_like_author_name(value: str) -> bool:
    cleaned = value.strip()
    if len(cleaned) < 2 or len(cleaned) > 120:
        return False
    lowered = cleaned.lower()
    if lowered in {"view profile", "follow", "connect", "message"}:
        return False
    if "http" in lowered or "linkedin.com" in lowered:
        return False
    if cleaned.count("\n") > 1:
        return False
    return True


def _clean_author_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.replace("\n", " ")).strip()
    if " • " in cleaned:
        cleaned = cleaned.split(" • ", 1)[0].strip()
    return cleaned


def _looks_like_headline(value: str, author_name: str) -> bool:
    cleaned = re.sub(r"\s+", " ", value.replace("\n", " ")).strip()
    if len(cleaned) < 3 or len(cleaned) > 300:
        return False
    if _clean_author_name(cleaned).casefold() == _clean_author_name(author_name).casefold():
        return False
    if _TIME_OR_META_RE.search(cleaned):
        return False
    if cleaned.startswith("•"):
        return False
    return True


def _first_text(container: Locator, selectors: tuple[str, ...]) -> str | None:
    for sel in selectors:
        v = _maybe_inner_text(container.locator(sel))
        if v:
            return v
    return None


def _normalize_profile_href(href: str | None) -> str | None:
    if not isinstance(href, str):
        return None
    href = href.strip()
    if not href:
        return None
    base = href.split("?", 1)[0]
    if base.startswith("/"):
        return f"https://www.linkedin.com{base}"
    return base


def _is_profile_href(href: str) -> bool:
    lowered = href.strip().lower()
    if not lowered:
        return False
    return not any(token in lowered for token in _BAD_HREF_TOKENS)


def _name_from_profile_link(link: Locator) -> str | None:
    aria = (link.get_attribute("aria-label") or "").strip()
    if aria and (m := _VIEW_PROFILE_RE.match(aria)):
        name = _clean_author_name(m.group(1))
        if _looks_like_author_name(name):
            return name

    for span_sel in ("span[aria-hidden='true']", "span"):
        candidate = _maybe_inner_text(link.locator(span_sel))
        if candidate and _looks_like_author_name(candidate):
            return _clean_author_name(candidate)

    candidate = _maybe_inner_text(link)
    if candidate and _looks_like_author_name(candidate):
        return _clean_author_name(candidate)
    return None


def _pick_author_profile_link(container: Locator) -> tuple[Locator | None, str | None]:
    try:
        links = container.locator(_PROFILE_LINK_SELECTOR)
        count = links.count()
        for i in range(min(count, 8)):
            link = links.nth(i)
            href = (link.get_attribute("href") or "").strip()
            if not href or not _is_profile_href(href):
                continue
            name = _name_from_profile_link(link)
            if name:
                return link, name
    except Exception:
        return None, None
    return None, None


def _headline_near_profile_link(link: Locator, author_name: str) -> str | None:
    try:
        actor = link.locator(
            "xpath=ancestor::*[contains(@class,'actor') or contains(@class,'Actor')][1]"
        ).first
        scope = actor if actor.count() > 0 else link.locator("xpath=ancestor::div[1]").first
        if scope.count() <= 0:
            return None

        candidates = scope.locator(
            "span[aria-hidden='true'], span[class*='description'], span[class*='subtitle']"
        )
        for i in range(min(candidates.count(), 24)):
            txt = _maybe_inner_text(candidates.nth(i))
            if txt and _looks_like_headline(txt, author_name):
                return re.sub(r"\s+", " ", txt.replace("\n", " ")).strip()
    except Exception:
        return None
    return None


def _urn_from_profile_link(link: Locator) -> str | None:
    try:
        for attr in _URN_ATTRS:
            val = link.get_attribute(attr)
            if isinstance(val, str) and "urn:li" in val:
                return val.strip()
        href = link.get_attribute("href") or ""
        if m := re.search(r"miniProfileUrn=([^&]+)", href):
            return unquote(m.group(1)).strip()
    except Exception:
        return None
    return None


def extract_author_name(container: Locator) -> str | None:
    legacy = _first_text(container, _LEGACY_NAME_SELECTORS)
    if legacy:
        return _clean_author_name(legacy)

    _, name = _pick_author_profile_link(container)
    return name


def _headline_from_actor_block(link: Locator, author_name: str) -> str | None:
    try:
        actor = link.locator(
            "xpath=ancestor::*[contains(@class,'actor') or contains(@class,'Actor')][1]"
        ).first
        if actor.count() <= 0:
            return None
        raw = actor.inner_text()
        for line in raw.split("\n"):
            cleaned = re.sub(r"\s+", " ", line).strip()
            if cleaned and _looks_like_headline(cleaned, author_name):
                return cleaned
    except Exception:
        return None
    return None


def extract_author_headline(container: Locator, *, author_name: str | None = None) -> str | None:
    legacy = _first_text(container, _LEGACY_HEADLINE_SELECTORS)
    if legacy:
        return legacy

    wildcard = _first_text(container, _HEADLINE_WILDCARD_SELECTORS)
    if wildcard and (not author_name or _looks_like_headline(wildcard, author_name)):
        return wildcard

    if author_name:
        link, _ = _pick_author_profile_link(container)
        if link is not None:
            near = _headline_near_profile_link(link, author_name)
            if near:
                return near
            block = _headline_from_actor_block(link, author_name)
            if block:
                return block
    return None


def extract_author_profile_url(container: Locator) -> str | None:
    link, _ = _pick_author_profile_link(container)
    if link is not None:
        return _normalize_profile_href(link.get_attribute("href"))

    try:
        first = container.locator(_PROFILE_LINK_SELECTOR).first
        if first.count() <= 0:
            return None
        return _normalize_profile_href(first.get_attribute("href"))
    except Exception:
        return None


def extract_author_fields(container: Locator) -> dict[str, Any]:
    legacy_name = _first_text(container, _LEGACY_NAME_SELECTORS)
    name = _clean_author_name(legacy_name) if legacy_name else None

    link: Locator | None = None
    if not name:
        link, name = _pick_author_profile_link(container)
    else:
        link, matched = _pick_author_profile_link(container)
        if matched and _clean_author_name(matched).casefold() == name.casefold():
            pass
        elif link is None:
            link, _ = _pick_author_profile_link(container)

    profile_url = (
        _normalize_profile_href(link.get_attribute("href"))
        if link is not None
        else extract_author_profile_url(container)
    )
    headline = extract_author_headline(container, author_name=name)
    urn = _urn_from_profile_link(link) if link is not None else None

    # region agent log
    if name:
        headline_probe: dict[str, int] = {}
        for sel in _LEGACY_HEADLINE_SELECTORS + _HEADLINE_WILDCARD_SELECTORS:
            try:
                headline_probe[sel] = container.locator(sel).count()
            except Exception:
                headline_probe[sel] = -1
        agent_dbg_log(
            run_id="post-fix",
            hypothesis_id="H2",
            location="author_extract.py:extract_author_fields",
            message="Author field extraction snapshot",
            data={
                "has_name": bool(name),
                "has_headline": bool(headline),
                "has_profile_url": bool(profile_url),
                "has_urn": bool(urn),
                "headline_probe": headline_probe,
                "profile_links": _profile_link_count(container),
            },
        )
    # endregion

    if not name:
        return {"name": None, "headline": None, "profile_url": None, "urn": None}
    return {
        "name": name,
        "headline": headline,
        "profile_url": profile_url,
        "urn": urn,
    }
