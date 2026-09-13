from __future__ import annotations

"""
Jobs DOM -> domain parsing (best-effort).
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page

from ..models.job import Job
from .job_insights import classify_job_insights

_JOB_ID_RE = re.compile(r"/jobs/view/(\d+)", re.IGNORECASE)


def _job_id_from_url(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None
    m = _JOB_ID_RE.search(url)
    return m.group(1) if m else None


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

        anchors = page.locator(self.job_card_anchor_selector)
        count = anchors.count()
        out: list[Job] = []
        seen_ids = set(skip_ids or ())

        for idx in range(min(limit, count)):
            try:
                a = anchors.nth(idx)
                href = a.get_attribute("href")
                url = _normalize_url(href) or href
                job_id = _job_id_from_url(url)
                if job_id and job_id in seen_ids:
                    continue

                # Select the list card so the split panel updates without
                # navigating to /jobs/view (that page opens reaction dialogs).
                card = _closest_card(a)
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

                title = _first_text(
                    page.locator("h1.t-24"),
                    page.locator(".job-details-jobs-unified-top-card__job-title"),
                    a.locator("span[aria-hidden='true']"),
                    a,
                )
                # Company/location live on the card container or details
                # panel — not inside the title <a>.
                company = _first_text(
                    page.locator(".job-details-jobs-unified-top-card__company-name"),
                    page.locator(".jobs-unified-top-card__company-name"),
                    card.locator(".artdeco-entity-lockup__subtitle"),
                    card.locator(".job-card-container__primary-description"),
                    card.locator("[data-view-name='job-card-company-name']"),
                    a.locator("span.job-card-container__primary-description"),
                )
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
                    a.locator("li.job-card-container__metadata-item"),
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

