"""Compatibility facade. Session lives in linkedin-search-core; searches delegate to jobs and posts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from linkedin_search_core.auth.email_password import EmailPasswordLoginFlow
from linkedin_search_core.auth.social import SocialLoginFlow
from linkedin_search_core.session import LinkedInSession
from linkedin_search_jobs import JobSearch
from linkedin_search_jobs.models.job import Job
from linkedin_search_posts import PostSearch
from linkedin_search_posts.models.post import Post

__all__ = [
    "EmailPasswordLoginFlow",
    "Job",
    "LinkedInClient",
    "Post",
    "PostSearch",
    "SocialLoginFlow",
]


class LinkedInClient(LinkedInSession):
    """Worker-facing client. Job and post collection delegate to the search packages."""

    def read_posts(self, *, limit: int = 10) -> list[dict[str, Any]]:
        return PostSearch(self).read(limit=limit)

    def fetch_posts(self, *, limit: int = 10) -> list[Post]:
        return PostSearch(self).fetch(limit=limit)

    def fetch_jobs(
        self,
        *,
        keywords: str,
        location: str | None = None,
        limit: int = 25,
        filters: Mapping[str, Any] | None = None,
    ) -> list[Job]:
        return JobSearch(self).fetch(
            keywords=keywords,
            location=location,
            limit=limit,
            filters=filters,
        )
