from __future__ import annotations

import html
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

from playwright.sync_api import Page

from ..models.job import Job
from ..navigation.job_search_url import build_jobs_search_query

_GUEST_SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_PAGE_SIZE = 10
_JOB_ID_RE = re.compile(r"urn:li:jobPosting:(\d+)")
_TITLE_RE = re.compile(
    r'class="[^"]*base-search-card__title[^"]*"[^>]*>(.*?)</h3>',
    re.IGNORECASE | re.DOTALL,
)
_COMPANY_RE = re.compile(
    r'class="[^"]*base-search-card__subtitle[^"]*"[^>]*>(.*?)</h4>',
    re.IGNORECASE | re.DOTALL,
)
_LOCATION_RE = re.compile(
    r'class="[^"]*job-search-card__location[^"]*"[^>]*>(.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


def guest_search_url(
    *,
    keywords: str,
    location: str | None,
    filters: Mapping[str, Any] | None,
    start: int,
) -> str:
    q = build_jobs_search_query(keywords=keywords, location=location, filters=filters)
    q["start"] = str(max(0, start))
    return f"{_GUEST_SEARCH}?{urlencode(q)}"


def parse_guest_jobs_html(html: str) -> list[Job]:
    if not html:
        return []
    out: list[Job] = []
    seen: set[str] = set()
    for match in _JOB_ID_RE.finditer(html):
        job_id = match.group(1)
        if job_id in seen:
            continue
        seen.add(job_id)
        chunk = html[match.start() : match.start() + 4000]
        title = _first_plain(chunk, _TITLE_RE)
        company = _first_plain(chunk, _COMPANY_RE)
        location = _first_plain(chunk, _LOCATION_RE)
        out.append(
            Job(
                job_id=job_id,
                job_url=f"https://www.linkedin.com/jobs/view/{job_id}",
                title=title,
                company=company,
                location=location,
            )
        )
    return out


def fetch_guest_jobs(
    page: Page,
    *,
    keywords: str,
    location: str | None,
    filters: Mapping[str, Any] | None,
    limit: int,
    skip_ids: set[str] | None = None,
) -> list[Job]:
    if limit <= 0:
        return []
    skip = set(skip_ids or ())
    collected: list[Job] = []
    start = 0
    locations = _location_fallbacks(location)
    for loc in locations:
        if len(collected) >= limit:
            break
        empty_pages = 0
        while len(collected) < limit and start < 100:
            url = guest_search_url(
                keywords=keywords,
                location=loc,
                filters=filters,
                start=start,
            )
            html, status = _get_html(page, url)
            if status != 200 or not html:
                empty_pages += 1
                if empty_pages >= 2:
                    break
                start += _PAGE_SIZE
                continue
            page_jobs = parse_guest_jobs_html(html)
            new_count = 0
            for job in page_jobs:
                if not job.job_id or job.job_id in skip:
                    continue
                if not job.title:
                    continue
                skip.add(job.job_id)
                collected.append(job)
                new_count += 1
                if len(collected) >= limit:
                    break
            if len(page_jobs) < _PAGE_SIZE:
                break
            if new_count == 0:
                empty_pages += 1
                if empty_pages >= 2:
                    break
            start += _PAGE_SIZE
        if len(collected) >= limit:
            break
        start = 0
    return collected[:limit]


def _location_fallbacks(location: str | None) -> list[str | None]:
    out: list[str | None] = []
    if isinstance(location, str) and location.strip():
        out.append(location.strip())
        lowered = location.casefold()
        if "лондон" in lowered and "london" not in lowered:
            out.append("London")
        if "london" in lowered or "лондон" in lowered:
            out.append("United Kingdom")
    else:
        out.append(None)
    # Unique while preserving order.
    seen: set[str] = set()
    unique: list[str | None] = []
    for item in out:
        key = item or ""
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _get_html(page: Page, url: str) -> tuple[str, int]:
    try:
        resp = page.request.get(url, timeout=15_000)
        return resp.text() or "", int(resp.status)
    except Exception:
        return "", 0


def _first_plain(markup: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(markup)
    if not match:
        return None
    text = html.unescape(_TAG_RE.sub("", match.group(1)))
    text = " ".join(text.split())
    return text or None
