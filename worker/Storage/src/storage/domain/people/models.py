from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class PeopleSearchRow(TypedDict):
    id: str
    user_id: str
    title: str
    search_query: str
    prompt: str
    search_tariff_id: NotRequired[str | None]
    status: str
    last_run_at: str | None
    linkedin_filters: NotRequired[dict[str, Any] | None]
    created_at: str
    updated_at: str


class PersonRow(TypedDict):
    id: str
    user_id: str
    linkedin_account_id: str
    source_key: str
    public_id: str | None
    profile_url: str
    full_name: str | None
    avatar_url: str | None
    headline: str | None
    location: str | None
    connection_degree: str | None
    about: str | None
    skills: list[str]
    current_company: str | None
    experience: list[dict[str, Any]]
    education: list[dict[str, Any]]
    raw_extra: dict[str, Any] | None
    fetched_at: str
    enriched_at: str | None
    created_at: str
    updated_at: str


class PeopleAnalysisUpsert(TypedDict):
    search_id: str
    person_id: str
    analyzed_at: str
    match: bool
    score: int
    reason: str
    matched_requirements: list[str]
    missing_requirements: list[str]
    red_flags: list[str]
    stage: NotRequired[str]
    raw_payload: NotRequired[dict[str, Any] | None]
    error: NotRequired[str | None]
    updated_at: NotRequired[str]
