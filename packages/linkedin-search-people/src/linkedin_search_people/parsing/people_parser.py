from __future__ import annotations

import re
from contextlib import suppress
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page

from linkedin_search_people.models.person import Person

_IN_RE = re.compile(r"/in/([^/?#]+)", re.IGNORECASE)
_DEGREE_RE = re.compile(r"\b([123](?:st|nd|rd)?\+?)\b", re.IGNORECASE)
_NAME_TRAIL_RE = re.compile(r"\s*[•·]\s*(?:\d[\d\s]*(st|nd|rd)\+?|[^\s].*)$", re.IGNORECASE)
_CTA_RE = re.compile(
    r"(?i)\b("
    r"установить контакт|отправить сообщение|написать сообщение|подписаться|"
    r"connect|message|follow|following"
    r")\b",
)
_CURRENT_ROLE_TAIL_RE = re.compile(
    r"(?i)[\s•·|,-]*(?:current|текущая)\s*:\s*.+$",
)
_CURRENT_ROLE_RE = re.compile(
    r"(?i)(?:current|текущая)\s*:\s*(.+?)(?=\s*[•·]|$)",
)
_HTTP_RE = re.compile(r"https?://[^\s,]+", re.IGNORECASE)
_GHOST_AVATAR_MARKERS: tuple[str, ...] = (
    "ghost-person",
    "ghost-company",
    "data:image",
    "static.licdn.com/aero-v1/",
    "/aero-v1/sc/h/",
)
_AVATAR_IMG_SELECTORS: tuple[str, ...] = (
    "img.pv-top-card-profile-picture__image",
    "img.profile-photo-edit__preview",
    ".pv-top-card--photo img",
    "button.pv-top-card-profile-picture img",
    ".entity-result__image img",
    "img.presence-entity__image",
    "img.EntityPhoto-circle-5",
    "img.EntityPhoto-circle-4",
    "img.EntityPhoto-circle-3",
    ".ivm-image-view-model img",
    ".ivm-view-attr__img--centered",
    "img[src*='profile-displayphoto']",
    "img[srcset*='profile-displayphoto']",
    "img[data-delayed-url*='profile-displayphoto']",
)
_CHROME_CLOSEST_JS = """el => Boolean(el.closest(
  'header, nav, #global-nav, .global-nav, .global-nav__me, .scaffold-layout__nav, '
  + '.msg-overlay-list-bubble, [data-test-global-nav]'
))"""


def clean_person_name(name: str | None) -> str | None:
    if not name:
        return None
    text = re.sub(r"\s+", " ", name).strip()
    text = _NAME_TRAIL_RE.sub("", text).strip()
    if len(text) > 80:
        text = text[:80].rstrip()
    lowered = text.lower()
    if lowered in {"linkedin member", "участник linkedin", "connect", "message"}:
        return None
    return text or None


def clean_headline(
    headline: str | None,
    *,
    location: str | None = None,
    name: str | None = None,
) -> str | None:
    if not headline:
        return None
    text = re.sub(r"\s+", " ", headline).strip()
    text = _CTA_RE.sub("", text).strip(" •·,-")
    text = _CURRENT_ROLE_TAIL_RE.sub("", text).strip(" •·,-")
    if name and text.casefold().startswith(name.casefold()):
        text = text[len(name) :].strip(" •·,-")
    m = _DEGREE_RE.search(text)
    if m and m.start() < 8:
        text = text[m.end() :].strip(" •·,-")
    if location:
        loc = location.strip()
        if loc and text.endswith(loc):
            text = text[: -len(loc)].strip(" •·,-")
        if loc and loc in text:
            text = text.replace(loc, " ").strip(" •·,-")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 160:
        text = text[:157].rstrip() + "…"
    return text or None


def extract_current_role(text: str | None) -> str | None:
    if not text:
        return None
    m = _CURRENT_ROLE_RE.search(text)
    if not m:
        return None
    role = m.group(1).strip(" •·,-")
    return role or None


def extract_public_id(url: str | None) -> str | None:
    if not url:
        return None
    m = _IN_RE.search(url)
    if not m:
        return None
    pid = m.group(1).strip().rstrip("/")
    return pid or None


def normalize_avatar_url(src: str | None) -> str | None:
    if not isinstance(src, str):
        return None
    src = src.strip()
    if not src.startswith("http"):
        match = _HTTP_RE.search(src)
        src = match.group(0) if match else ""
    if not src.startswith("http"):
        return None
    lowered = src.lower()
    if any(marker in lowered for marker in _GHOST_AVATAR_MARKERS):
        return None
    return src.rstrip("\\").rstrip(",")


def _best_srcset(srcset: str | None) -> str | None:
    if not srcset:
        return None
    best_url: str | None = None
    best_w = -1
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = normalize_avatar_url(bits[0])
        if not url:
            continue
        weight = 0
        if len(bits) > 1:
            token = bits[1].lower()
            with suppress(ValueError):
                if token.endswith("w"):
                    weight = int(token[:-1])
                elif token.endswith("x"):
                    weight = int(float(token[:-1]) * 1000)
        if weight >= best_w:
            best_w = weight
            best_url = url
    return best_url


def _is_chrome_el(el: Locator) -> bool:
    with suppress(Exception):
        return bool(el.evaluate(_CHROME_CLOSEST_JS))
    return False


def _avatar_score(url: str, *, public_id: str | None, img: Locator) -> int:
    lowered = url.lower()
    score = 0
    if "profile-displayphoto" in lowered or "profile-framedphoto" in lowered:
        score += 4
    elif "dms/image" in lowered:
        score += 1
    if public_id:
        with suppress(Exception):
            href = img.evaluate(
                """el => {
                  const a = el.closest('a[href*="/in/"]')
                    || el.parentElement?.querySelector('a[href*="/in/"]')
                    || el.parentElement?.parentElement?.querySelector('a[href*="/in/"]');
                  return a ? a.getAttribute('href') || '' : '';
                }"""
            )
            if isinstance(href, str) and f"/in/{public_id}".lower() in href.lower():
                score += 5
    return score


def _avatar_from_img(img: Locator) -> str | None:
    if _is_chrome_el(img):
        return None
    with suppress(Exception):
        for attr in ("src", "data-delayed-url", "data-src"):
            url = normalize_avatar_url(img.get_attribute(attr))
            if url:
                return url
        url = _best_srcset(img.get_attribute("srcset") or img.get_attribute("data-srcset"))
        if url:
            return url
        current = img.evaluate("el => el.currentSrc || ''")
        return normalize_avatar_url(current if isinstance(current, str) else None)
    return None


def extract_avatar_url(root: Locator, *, public_id: str | None = None) -> str | None:
    best: str | None = None
    best_score = -1
    selectors = list(_AVATAR_IMG_SELECTORS)
    if public_id:
        selectors = [
            f'a[href*="/in/{public_id}"] img',
            f'a[href*="/in/{public_id}"] ~ img',
            *selectors,
        ]
    for sel in selectors:
        loc = root.locator(sel)
        with suppress(Exception):
            n = min(loc.count(), 6)
            for i in range(n):
                img = loc.nth(i)
                url = _avatar_from_img(img)
                if not url:
                    continue
                score = _avatar_score(url, public_id=public_id, img=img)
                if score > best_score:
                    best_score = score
                    best = url
                    if score >= 8:
                        return best
    return best


def normalize_profile_url(url: str | None) -> str | None:
    if not url:
        return None
    raw = url.strip()
    if raw.startswith("/"):
        raw = f"https://www.linkedin.com{raw}"
    parsed = urlparse(raw)
    pid = extract_public_id(raw)
    if not pid:
        return None
    host = parsed.netloc or "www.linkedin.com"
    return f"https://{host}/in/{pid}"


def _text(loc: Locator) -> str:
    with suppress(Exception):
        t = (loc.inner_text() or "").strip()
        if t:
            return re.sub(r"\s+", " ", t)
    return ""


def _first_href(root: Locator) -> str | None:
    with suppress(Exception):
        link = root.locator("a[href*='/in/']").first
        if link.count() == 0:
            return None
        href = link.get_attribute("href")
        return href
    return None


def parse_person_card(root: Locator) -> Person | None:
    href = _first_href(root)
    profile_url = normalize_profile_url(href)
    public_id = extract_public_id(profile_url)
    if not profile_url or not public_id:
        return None

    name = ""
    for sel in (
        "span.entity-result__title-text a span[aria-hidden='true']",
        "a[href*='/in/'] span[aria-hidden='true']",
        ".entity-result__title-text span[aria-hidden='true']",
    ):
        name = _text(root.locator(sel).first)
        cleaned = clean_person_name(name)
        if cleaned:
            name = cleaned
            break
        name = ""
    if not name:
        name = public_id.replace("-", " ").title()
    else:
        name = clean_person_name(name) or name

    headline = ""
    for sel in (
        "div.entity-result__primary-subtitle",
        "div.entity-result__summary-line",
        "div.entity-result__subtitle",
    ):
        headline = _text(root.locator(sel).first)
        if headline:
            break

    location = ""
    for sel in (
        "div.entity-result__secondary-subtitle",
        "div.t-14.t-normal",
    ):
        location = _text(root.locator(sel).first)
        if location and location != headline:
            break
        location = ""

    snippet = _text(root.locator("p.entity-result__summary, p.entity-result__content-summary").first)

    current_company = extract_current_role(headline) or extract_current_role(snippet)
    headline = clean_headline(headline, location=location or None, name=name) or headline or None
    if current_company and headline:
        headline = _CURRENT_ROLE_TAIL_RE.sub("", headline).strip(" •·,-") or headline

    degree = None
    blob = " ".join(x for x in (name, headline, location, _text(root)) if x)
    m = _DEGREE_RE.search(blob)
    if m:
        token = m.group(1).lower()
        if token.startswith("1"):
            degree = "1st"
        elif token.startswith("2"):
            degree = "2nd"
        else:
            degree = "3rd+"
    with suppress(Exception):
        dist = _text(root.locator("span.dist-value, span.entity-result__badge-text").first)
        if "1" in dist:
            degree = "1st"
        elif "2" in dist:
            degree = "2nd"
        elif "3" in dist:
            degree = "3rd+"

    return Person(
        public_id=public_id,
        profile_url=profile_url,
        full_name=name or None,
        avatar_url=extract_avatar_url(root, public_id=public_id),
        headline=headline or None,
        location=location or None,
        connection_degree=degree,
        snippet=snippet or None,
        current_company=current_company,
    )


class PeopleParser:
    card_selectors: tuple[str, ...] = (
        "div.reusable-search__result-container",
        "li.reusable-search__result-container",
        "div[data-chameleon-result-urn]",
        "li.reusable-search__result-container li",
        "div.entity-result",
    )

    def parse_people(self, page: Page, *, limit: int, skip_ids: set[str] | None = None) -> list[Person]:
        skip = skip_ids or set()
        results: list[Person] = []
        seen: set[str] = set(skip)

        cards: list[Locator] = []
        for sel in self.card_selectors:
            loc = page.locator(sel)
            with suppress(Exception):
                count = loc.count()
                if count > 0:
                    cards = [loc.nth(i) for i in range(min(count, max(limit * 3, 30)))]
                    break

        if not cards:
            loc = page.locator("a[href*='/in/']")
            with suppress(Exception):
                count = loc.count()
                for i in range(min(count, max(limit * 3, 30))):
                    link = loc.nth(i)
                    if _is_chrome_el(link):
                        continue
                    href = link.get_attribute("href")
                    url = normalize_profile_url(href)
                    pid = extract_public_id(url)
                    if not url or not pid or pid in seen:
                        continue
                    seen.add(pid)
                    name = _text(link)
                    results.append(
                        Person(
                            public_id=pid,
                            profile_url=url,
                            full_name=name or pid,
                            avatar_url=extract_avatar_url(link, public_id=pid),
                        ),
                    )
                    if len(results) >= limit:
                        return results
            return results

        for card in cards:
            person = parse_person_card(card)
            if person is None or not person.public_id or person.public_id in seen:
                continue
            seen.add(person.public_id)
            results.append(person)
            if len(results) >= limit:
                break
        return results
