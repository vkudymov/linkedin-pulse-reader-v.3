from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from typing import Any

from linkedin_search_core.exceptions import BrowserLifecycleError, FeedLoadError
from linkedin_search_core.session import LinkedInSession
from linkedin_search_core.loading.scroller import HumanScroller
from linkedin_search_people.loading.people_waiter import PeopleWaiter
from linkedin_search_people.models.person import Person
from linkedin_search_people.navigation.boolean_query import normalize_boolean_query
from linkedin_search_people.navigation.people import PeopleNavigator
from linkedin_search_people.parsing.people_parser import PeopleParser
from linkedin_search_people.parsing.profile_parser import ProfileParser


class PeopleSearch:
    """Collect LinkedIn people search results from an open LinkedInSession."""

    def __init__(self, session: LinkedInSession) -> None:
        self._session = session

    def fetch(
        self,
        *,
        keywords: str,
        limit: int = 25,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Person]:
        session = self._session
        if not session._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        if limit <= 0:
            return []
        query = normalize_boolean_query(keywords or "").query
        if not query:
            extra = ""
            if isinstance(filters, Mapping):
                extra = str(filters.get("keywords") or "").strip()
            query = extra
        if not query:
            return []

        navigator = PeopleNavigator()
        waiter = PeopleWaiter(timeout_ms=session._client_cfg.browser.timeout_ms)
        scroller = HumanScroller(config=session._client_cfg.scroll)
        parser = PeopleParser()

        def person_key(p: Person) -> str | None:
            if p.public_id:
                return p.public_id
            if p.profile_url:
                return p.profile_url
            return None

        for attempt in range(2):
            try:
                navigator.goto_search(session.page, keywords=query, filters=filters)
                waiter.wait_for_people_ready(session.page)

                results: list[Person] = []
                seen: set[str] = set()

                def merge(new_people: list[Person]) -> None:
                    for p in new_people:
                        k = person_key(p)
                        if not k or k in seen:
                            continue
                        seen.add(k)
                        results.append(p)

                parse_limit = min(max(limit * 2, 40), 200)
                merge(parser.parse_people(session.page, limit=parse_limit, skip_ids=seen))
                if len(results) >= limit:
                    return results[:limit]

                no_progress = 0
                max_scrolls = session._client_cfg.scroll.max_scrolls
                for _ in range(max_scrolls):
                    before_len = len(results)
                    scroller.scroll_batch(page=session.page)
                    with suppress(Exception):
                        session.page.wait_for_load_state("networkidle", timeout=1500)
                    session.page.wait_for_timeout(250)
                    merge(
                        parser.parse_people(
                            session.page,
                            limit=min(max(limit * 2, 40), 200),
                            skip_ids=seen,
                        )
                    )
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
        return []

    def search(
        self,
        *,
        keywords: str,
        limit: int = 25,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Person]:
        return self.fetch(keywords=keywords, limit=limit, filters=filters)

    def enrich(self, profile_url: str) -> Person:
        session = self._session
        if not session._entered:
            raise BrowserLifecycleError(
                "Client not started. Use LinkedInClient as a context manager."
            )
        navigator = PeopleNavigator()
        waiter = PeopleWaiter(timeout_ms=session._client_cfg.browser.timeout_ms)
        navigator.goto_profile(session.page, profile_url=profile_url)
        waiter.wait_for_profile_ready(session.page)
        with suppress(Exception):
            session.page.wait_for_timeout(400)
        return ProfileParser().parse_profile(session.page, fallback_url=profile_url)
