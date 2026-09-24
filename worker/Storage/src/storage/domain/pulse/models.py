from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class LinkedInAccountRow(TypedDict):
    id: str
    user_id: str
    label: str | None
    li_profile_url: str | None
    cookies_json: list[dict[str, Any]]
    cookies_updated_at: str | None
    created_at: str
    updated_at: str
    session_snapshot: NotRequired[dict[str, Any] | None]


class LinkedInAccountCreate(TypedDict):
    user_id: str
    cookies_json: list[dict[str, Any]]
    label: NotRequired[str | None]
    li_profile_url: NotRequired[str | None]
    cookies_updated_at: NotRequired[str | None]
    session_snapshot: NotRequired[dict[str, Any] | None]


class FeedPostRow(TypedDict):
    id: str
    linkedin_account_id: str
    source_key: str
    urn: str | None
    post_url: str
    author_json: dict[str, Any] | None
    content: str | None
    published_at_text: str | None
    reactions_count: int | None
    comments_count: int | None
    media_urls: list[str]
    raw_extra: dict[str, Any] | None
    is_relevant: bool | None
    comment_text: str | None
    analysis_error: str | None
    analysis_payload: dict[str, Any] | None
    fetched_at: str
    analyzed_at: str | None


class FeedPostUpsert(TypedDict):
    linkedin_account_id: str
    source_key: str
    fetched_at: str
    post_url: str
    urn: NotRequired[str | None]
    author_json: NotRequired[dict[str, Any] | None]
    content: NotRequired[str | None]
    published_at_text: NotRequired[str | None]
    reactions_count: NotRequired[int | None]
    comments_count: NotRequired[int | None]
    media_urls: NotRequired[list[str]]
    raw_extra: NotRequired[dict[str, Any] | None]


class PostSearchRow(TypedDict):
    id: str
    user_id: str
    title: str
    search_prompt: str
    comment_prompt: str | None
    account_label: str | None
    search_tariff_id: NotRequired[str | None]
    email_report_enabled: NotRequired[bool]
    email_report_format: NotRequired[str]
    status: str
    last_run_at: str | None
    created_at: str
    updated_at: str


class PostSearchCreate(TypedDict):
    user_id: str
    title: str
    search_prompt: str
    comment_prompt: NotRequired[str | None]
    account_label: NotRequired[str | None]
    search_tariff_id: NotRequired[str | None]
    email_report_enabled: NotRequired[bool]
    email_report_format: NotRequired[str]
    status: NotRequired[str]
    last_run_at: NotRequired[str | None]


class PostAnalysisUpsert(TypedDict):
    post_search_id: str
    feed_post_id: str
    match: bool
    score: int
    reason: str
    matched_requirements: NotRequired[list[Any]]
    missing_requirements: NotRequired[list[Any]]
    red_flags: NotRequired[list[Any]]
    comment_text: NotRequired[str | None]
    comment_error: NotRequired[str | None]
    raw_payload: NotRequired[dict[str, Any] | None]
    error: NotRequired[str | None]
    analyzed_at: NotRequired[str | None]
    created_at: NotRequired[str | None]
    updated_at: NotRequired[str | None]

