from __future__ import annotations

"""
Jobs DOM -> domain parsing (best-effort).
"""

import re
from contextlib import suppress
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, Page

from ..models.job import Job
from .job_insights import classify_job_insights

_JOB_ID_RE = re.compile(r"/jobs/view/(\d+)", re.IGNORECASE)


def _job_id_from_url(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None
    m = _JOB_ID_RE.search(url)
    return m.group(1) if m else None


def _job_id_from_page_url(url: str | None) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    raw = (parse_qs(urlparse(url).query).get("currentJobId") or [None])[0]
    if isinstance(raw, str) and raw.isdigit():
        return raw
    return None


_SEMANTIC_CARD_SELECTORS = (
    "div[role='button'][componentkey^='job-card']",
    "div[componentkey^='job-card-component-ref-']",
    "div[role='button'][componentkey]:has(div[data-display-contents])",
)
_VERIFIED_JOB_RE = re.compile(
    r"\s*\((?:подтвержденная вакансия|verified job)\)\s*",
    re.IGNORECASE,
)
_SELECTED_PREFIX_RE = re.compile(
    r"^(?:Выбрано|Selected),\s*[«\"“](.+?)[»\"”]\s*$",
    re.IGNORECASE,
)
_COMPONENT_JOB_ID_RE = re.compile(r"(\d{6,})")


def _normalize_url(url: str | None) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        p = urlparse(url.strip())
        if not p.scheme or not p.netloc:
            return url.strip()
        return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")
    except Exception:
        return url.strip()


_LIST_CARD_SELECTOR = (
    "li[data-occludable-job-id], "
    "div[data-job-id], "
    "li.scaffold-layout__list-item:has(a[href*='/jobs/view/']), "
    "div.job-card-container"
)


@dataclass(frozen=True, slots=True)
class JobParser:
    job_card_anchor_selector: str = "a[href*='/jobs/view/']"

    def parse_jobs(
        self,
        page: Page,
        *,
        limit: int,
        skip_ids: set[str] | None = None,
    ) -> list[Job]:
        if "/jobs/view/" in (page.url or ""):
            try:
                page.go_back(wait_until="domcontentloaded")
            except Exception:
                return []

        cards = page.locator(_LIST_CARD_SELECTOR)
        count = cards.count()
        using_list_cards = count > 0
        using_semantic = False
        if not using_list_cards:
            for sel in _SEMANTIC_CARD_SELECTORS:
                loc = page.locator(sel)
                n = loc.count()
                if n > 0:
                    cards = loc
                    count = n
                    using_semantic = True
                    break
        if not using_list_cards and not using_semantic:
            cards = page.locator(self.job_card_anchor_selector)
            count = cards.count()
        out: list[Job] = []
        seen_ids = set(skip_ids or ())

        for idx in range(min(limit, count)):
            try:
                card = cards.nth(idx)
                href = None
                if using_semantic:
                    with suppress(Exception):
                        already = _job_id_from_componentkey(card.get_attribute("componentkey"))
                        if already and already in seen_ids:
                            continue
                    job_id = _select_semantic_card(page, card)
                elif not using_list_cards:
                    href = card.get_attribute("href")
                    if href and "isJobSearch=false" in href:
                        continue
                    card = _closest_card(card)
                    job_id = (
                        card.get_attribute("data-occludable-job-id")
                        or card.get_attribute("data-job-id")
                        or _job_id_from_url(href)
                    )
                else:
                    with suppress(Exception):
                        if card.locator("a[href*='/jobs/view/']").count() > 0:
                            href = card.locator("a[href*='/jobs/view/']").first.get_attribute("href")
                    job_id = (
                        card.get_attribute("data-occludable-job-id")
                        or card.get_attribute("data-job-id")
                        or _job_id_from_url(href)
                    )
                url = _normalize_url(href) or (
                    f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else href
                )
                if job_id and job_id in seen_ids:
                    continue
                if not job_id and not url:
                    continue

                # Semantic cards are already selected in _select_semantic_card.
                if not using_semantic:
                    try:
                        card.click(timeout=2_000)
                        page.wait_for_selector(
                            "div.jobs-description-content__text, "
                            "div.jobs-description__content, "
                            "div#job-details, "
                            ".job-details-jobs-unified-top-card__company-name",
                            timeout=2_500,
                        )
                    except Exception:
                        pass

                title = _clean_job_title(
                    _first_text(
                        card.locator("a.job-card-list__title"),
                        card.locator(".job-card-list__title--link"),
                        card.locator("a.job-card-container__link"),
                        card.locator(".artdeco-entity-lockup__title"),
                        page.locator(".job-details-jobs-unified-top-card__job-title"),
                        card.locator("div[data-display-contents] > p"),
                        card.locator("p"),
                        card.locator("span[aria-hidden='true']"),
                    )
                )
                doc_title, doc_company = _title_company_from_document(page)
                if not title:
                    title = doc_title
                # Company/location live on the card container or details
                # panel — not inside the title <a>.
                company = _first_text(
                    page.locator(".job-details-jobs-unified-top-card__company-name"),
                    page.locator(".jobs-unified-top-card__company-name"),
                    card.locator(".artdeco-entity-lockup__subtitle"),
                    card.locator(".job-card-container__primary-description"),
                    card.locator("[data-view-name='job-card-company-name']"),
                    card.locator("span.job-card-container__primary-description"),
                    card.locator("div[data-display-contents] > p").nth(1),
                )
                if not company:
                    company = doc_company
                company_url = _first_href(
                    page.locator(".job-details-jobs-unified-top-card__company-name a"),
                    page.locator("a.job-details-jobs-unified-top-card__company-name"),
                    page.locator(".jobs-unified-top-card__company-name a"),
                    card.locator("a[href*='/company/']"),
                    card.locator("a[href*='/school/']"),
                )
                location = _first_text(
                    page.locator(
                        ".job-details-jobs-unified-top-card__primary-description-container"
                    ),
                    page.locator(".job-details-jobs-unified-top-card__bullet"),
                    page.locator("span.jobs-unified-top-card__bullet"),
                    card.locator("li.job-card-container__metadata-item"),
                    card.locator(".job-card-container__metadata-wrapper"),
                    card.locator(".artdeco-entity-lockup__caption"),
                    card.locator("li.job-card-container__metadata-item"),
                )

                description = _first_text(
                    page.locator("div.jobs-description-content__text"),
                    page.locator("div.jobs-description__content"),
                    page.locator("div#job-details"),
                )
                posted_at = _first_text(
                    page.locator("span.jobs-unified-top-card__posted-date"),
                    page.locator("span.jobs-unified-top-card__bullet"),
                )
                insight_texts = _all_texts(
                    page.locator(".job-details-fit-level-preferences button"),
                    page.locator(".job-details-fit-level-preferences li"),
                    page.locator("button.job-details-jobs-unified-top-card__job-insight-text-button"),
                    page.locator("li.job-details-jobs-unified-top-card__job-insight"),
                    page.locator(".job-details-jobs-unified-top-card__job-insight"),
                    card.locator("li.job-card-container__metadata-item"),
                )
                insights = classify_job_insights(
                    insight_texts,
                    location=location,
                    description=description,
                )

                out.append(
                    Job(
                        job_id=job_id,
                        job_url=url,
                        title=title,
                        company=company,
                        company_url=company_url,
                        location=location,
                        description=description,
                        posted_at_text=posted_at,
                        workplace_type=insights.workplace_type,
                        employment_type=insights.employment_type,
                        insights=insights.labels,
                    ),
                )
                if job_id:
                    seen_ids.add(job_id)
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                if "/jobs/view/" in (page.url or ""):
                    try:
                        page.go_back(wait_until="domcontentloaded")
                    except Exception:
                        pass
            except Exception:
                # Isolate failures per job card.
                continue

        return out


def _job_id_from_componentkey(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    m = _COMPONENT_JOB_ID_RE.search(value)
    return m.group(1) if m else None


def _select_semantic_card(page: Page, card: Locator) -> str | None:
    """Click an AI search-results card and read currentJobId from the URL."""
    from_key = None
    with suppress(Exception):
        from_key = _job_id_from_componentkey(card.get_attribute("componentkey"))
    before = _job_id_from_page_url(page.url)
    with suppress(Exception):
        card.click(timeout=2_000)
        with suppress(Exception):
            page.wait_for_function(
                """(prev) => {
                    const id = new URL(location.href).searchParams.get('currentJobId');
                    return Boolean(id) && id !== prev;
                }""",
                arg=before or "",
                timeout=2_500,
            )
        with suppress(Exception):
            page.wait_for_selector(
                "div.jobs-description-content__text, "
                "div.jobs-description__content, "
                "div#job-details, "
                ".job-details-jobs-unified-top-card__company-name",
                timeout=2_500,
            )
    return _job_id_from_page_url(page.url) or from_key or before


def _clean_job_title(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    title = _VERIFIED_JOB_RE.sub("", lines[-1]).strip()
    selected = _SELECTED_PREFIX_RE.match(title)
    if selected:
        title = selected.group(1).strip()
    return title or None


def _title_company_from_document(page: Page) -> tuple[str | None, str | None]:
    with suppress(Exception):
        parts = [p.strip() for p in (page.title() or "").split(" | ") if p.strip()]
        if len(parts) >= 2 and parts[-1].casefold() == "linkedin":
            head = parts[0]
            title = head if head.casefold() not in {"jobs", "вакансии", "linkedin"} else None
            company = parts[1] if len(parts) >= 3 else None
            if company and company.casefold() in {"linkedin", "jobs", "вакансии"}:
                company = None
            return title, company
    return None, None


def _closest_card(anchor: Locator) -> Locator:
    """Title links do not wrap company/location; walk up to the card root."""
    for sel in (
        "xpath=ancestor::*[contains(@class,'job-card-container')][1]",
        "xpath=ancestor::li[contains(@class,'scaffold-layout__list-item')][1]",
        "xpath=ancestor::li[contains(@class,'jobs-search-results__list-item')][1]",
        "xpath=ancestor::div[contains(@class,'job-card-list')][1]",
        "xpath=ancestor::li[1]",
    ):
        loc = anchor.locator(sel)
        try:
            if loc.count() > 0:
                return loc.first
        except Exception:
            continue
    return anchor


def _first_href(*locators: Locator) -> str | None:
    for loc in locators:
        try:
            if loc.count() <= 0:
                continue
            href = loc.first.get_attribute("href")
            url = _normalize_url(href) or (href.strip() if isinstance(href, str) else None)
            if url:
                return url
        except Exception:
            continue
    return None


def _first_text(*locators: Locator) -> str | None:
    for loc in locators:
        try:
            if loc.count() <= 0:
                continue
            t = (loc.first.inner_text() or "").strip()
            if t:
                return t
        except Exception:
            continue
    return None


def _all_texts(*locators: Locator, limit: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for loc in locators:
        try:
            n = min(loc.count(), limit)
        except Exception:
            continue
        for i in range(n):
            try:
                t = " ".join((loc.nth(i).inner_text() or "").split())
            except Exception:
                continue
            key = t.casefold()
            if not t or key in seen or len(t) > 64:
                continue
            seen.add(key)
            out.append(t)
    return out

