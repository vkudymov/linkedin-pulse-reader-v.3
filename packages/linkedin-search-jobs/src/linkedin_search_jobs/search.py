from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from typing import Any

from linkedin_search_core.exceptions import BrowserLifecycleError, FeedLoadError
from linkedin_search_core.session import LinkedInSession
from linkedin_search_core.loading.scroller import HumanScroller
from linkedin_search_jobs.loading.jobs_waiter import JobsWaiter
from linkedin_search_jobs.models.job import Job
from linkedin_search_jobs.navigation.jobs import JobsNavigator
from linkedin_search_jobs.parsing.job_parser import JobParser


class JobSearch:
    """Collect LinkedIn job search results from an open LinkedInSession."""

    def __init__(self, session: LinkedInSession) -> None:
        self._session = session

    def fetch(
        self,
        *,
        keywords: str,
        location: str | None = None,
        limit: int = 25,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Job]:
        """
        High-level “fetch LinkedIn jobs search results” operation.

        Best-effort: selectors vary between accounts/AB tests. Returns partial data when needed.
        """
        session = self._session
        if not session._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        if limit <= 0:
            return []
        if not isinstance(keywords, str) or not keywords.strip():
            return []

        navigator = JobsNavigator()
        waiter = JobsWaiter(timeout_ms=session._client_cfg.browser.timeout_ms)
        scroller = HumanScroller(config=session._client_cfg.scroll)
        parser = JobParser()
        location_text = location.strip() if isinstance(location, str) else None

        def job_key(j: Job) -> str | None:
            if isinstance(j.job_id, str) and j.job_id.strip():
                return f"id:{j.job_id.strip()}"
            if isinstance(j.job_url, str) and j.job_url.strip():
                return f"url:{j.job_url.strip()}"
            return None

        for attempt in range(2):
            try:
                navigator.goto_search(
                    session.page,
                    keywords=keywords.strip(),
                    # Do not rely on URL `location=` guessing; we set it via UI below.
                    location=None,
                    filters=filters,
                )
                waiter.wait_for_jobs_ready(session.page)
                if location_text:
                    navigator.apply_location_first_match(session.page, location=location_text)

                results: list[Job] = []
                seen: set[str] = set()
                seen_job_ids: set[str] = set()

                def merge(new_jobs: list[Job]) -> None:
                    for j in new_jobs:
                        k = job_key(j)
                        if not k or k in seen:
                            continue
                        seen.add(k)
                        if isinstance(j.job_id, str) and j.job_id.strip():
                            seen_job_ids.add(j.job_id.strip())
                        results.append(j)

                def stay_on_search() -> None:
                    if "/jobs/view/" not in (session.page.url or ""):
                        return
                    with suppress(Exception):
                        session.page.keyboard.press("Escape")
                    with suppress(Exception):
                        session.page.go_back(wait_until="domcontentloaded")
                    if "/jobs/view/" in (session.page.url or ""):
                        navigator.goto_search(
                            session.page,
                            keywords=keywords.strip(),
                            location=None,
                            filters=filters,
                        )
                        waiter.wait_for_jobs_ready(session.page)
                        if location_text:
                            navigator.apply_location_first_match(session.page, location=location_text)

                parse_limit = min(max(limit * 2, 50), 250)
                parsed = parser.parse_jobs(
                    session.page,
                    limit=parse_limit,
                    skip_ids=seen_job_ids,
                )
                merge(parsed)
                stay_on_search()
                if len(results) >= limit:
                    return results[:limit]

                no_progress = 0
                max_scrolls = session._client_cfg.scroll.max_scrolls
                for _ in range(max_scrolls):
                    stay_on_search()
                    before_len = len(results)
                    scroller.scroll_batch(page=session.page)
                    with suppress(Exception):
                        session.page.wait_for_load_state("networkidle", timeout=1500)
                    session.page.wait_for_timeout(250)

                    parsed = parser.parse_jobs(
                        session.page,
                        limit=min(max(limit * 2, 50), 250),
                        skip_ids=seen_job_ids,
                    )
                    merge(parsed)
                    if len(results) >= limit:
                        return results[:limit]

                    if len(results) > before_len:
                        no_progress = 0
                    else:
                        no_progress += 1
                        if no_progress >= session._client_cfg.scroll.max_no_progress_scrolls:
                            break

                return results[:limit]
            except FeedLoadError:
                if attempt == 0:
                    session.page.reload(wait_until="domcontentloaded")
                    continue
                raise
        # Unreachable: loop either returns results or raises.
        return []

    def search(
        self,
        *,
        keywords: str,
        location: str | None = None,
        limit: int = 25,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Job]:
        """Alias of fetch()."""
        return self.fetch(keywords=keywords, location=location, limit=limit, filters=filters)
