from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Job:
    """
    Portable, provider-agnostic job listing representation.

    `source_key` must be stable across runs for deduplication/upserts (e.g. "job:12345").
    """

    source_key: str
    job_url: str
    title: str
    company: str | None = None
    company_url: str | None = None
    location: str | None = None
    description: str | None = None
    posted_at_text: str | None = None
    workplace_type: str | None = None
    employment_type: str | None = None
    raw: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class JobSearchSpec:
    """
    One user-defined job search configuration.

    `filter_prompt` must contain the marker <<<JOB_TEXT>>> (validated at the UI/API boundary).
    """

    job_search_id: str
    title: str
    search_query: str
    location: str | None
    filter_prompt: str
    limit: int = 25
    linkedin_filters: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class StoredJob:
    """
    Repository-returned handle to a persisted Job.

    `job_id` is an opaque repository identifier (uuid/str/etc).
    """

    job_id: str
    source_key: str
    job_url: str


@dataclass(frozen=True, slots=True)
class StoredJobAnalysis:
    job_search_id: str
    job_id: str
    analyzed_at: datetime
    match: bool
    score: int
    reason: str
    matched_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    red_flags: tuple[str, ...]
    raw_payload: Mapping[str, Any] | None = None
    error: str | None = None

