from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class JobSearchRow(TypedDict):
    id: str
    user_id: str
    title: str
    search_query: str
    location: str | None
    filter_prompt: str
    status: str  # "active" | "paused"
    last_run_at: str | None
    linkedin_filters: NotRequired[dict[str, Any] | None]
    created_at: str
    updated_at: str


class JobSearchCreate(TypedDict):
    user_id: str
    title: str
    search_query: str
    filter_prompt: str
    location: NotRequired[str | None]
    status: NotRequired[str]
    last_run_at: NotRequired[str | None]
    linkedin_filters: NotRequired[dict[str, Any] | None]


class JobRow(TypedDict):
    id: str
    user_id: str
    linkedin_account_id: str
    source_key: str
    linkedin_job_id: str | None
    job_url: str
    title: str
    company: str | None
    location: str | None
    description: str | None
    raw_extra: dict[str, Any] | None
    fetched_at: str
    created_at: str
    updated_at: str


class JobUpsert(TypedDict):
    user_id: str
    linkedin_account_id: str
    source_key: str
    job_url: str
    title: str
    fetched_at: str
    linkedin_job_id: NotRequired[str | None]
    company: NotRequired[str | None]
    location: NotRequired[str | None]
    description: NotRequired[str | None]
    raw_extra: NotRequired[dict[str, Any] | None]
    updated_at: NotRequired[str]


class JobAnalysisUpsert(TypedDict):
    job_search_id: str
    job_id: str
    analyzed_at: str
    match: bool
    score: int
    reason: str
    matched_requirements: list[str]
    missing_requirements: list[str]
    red_flags: list[str]
    raw_payload: NotRequired[dict[str, Any] | None]
    error: NotRequired[str | None]
    updated_at: NotRequired[str]

