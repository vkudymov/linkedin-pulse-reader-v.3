from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class AdminUserRow(BaseModel):
    id: str
    email: str | None = None
    created_at: datetime | None = None

    full_name: str | None = None
    is_admin: bool
    is_blocked: bool
    blocked_at: datetime | None = None
    post_search_run_count: int


class AdminUserProfileDetails(BaseModel):
    id: str
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    company: str | None = None
    job_title: str | None = None
    date_of_birth: date | None = None
    city: str | None = None
    bio: str | None = None
    website: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminUserProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    company: str | None = None
    job_title: str | None = None
    date_of_birth: str | None = None
    city: str | None = None
    bio: str | None = None
    website: str | None = None


class AdminUserPromptsDetails(BaseModel):
    id: str
    search_prompt: str | None = None
    comment_prompt: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminUserPromptsUpdate(BaseModel):
    search_prompt: str | None = None
    comment_prompt: str | None = None


class AdminLinkedInAccountRow(BaseModel):
    id: str
    label: str | None = None
    li_profile_url: str | None = None
    created_at: datetime | None = None


class AdminFeedPostRow(BaseModel):
    id: str
    linkedin_account_id: str
    source_key: str | None = None
    urn: str | None = None
    post_url: str | None = None
    author_json: dict[str, Any] | None = None
    content: str | None = None
    published_at_text: str | None = None
    reactions_count: int | None = None
    comments_count: int | None = None
    media_urls: list[str] = []
    raw_extra: dict[str, Any] | None = None
    is_relevant: bool | None = None
    comment_text: str | None = None
    analysis_error: str | None = None
    analysis_payload: dict[str, Any] | None = None
    fetched_at: datetime | None = None
    analyzed_at: datetime | None = None


class AdminFeedPostMediaRow(BaseModel):
    id: str
    feed_post_id: str
    original_url: str | None = None
    object_path: str | None = None
    public_url: str | None = None
    position: int | None = None
    created_at: datetime | None = None


class AdminPostCounts(BaseModel):
    all: int
    relevant: int
    rejected: int
    pending: int


class AdminUserPostsResponse(BaseModel):
    accounts: list[AdminLinkedInAccountRow]
    posts: list[AdminFeedPostRow]
    media_by_post_id: dict[str, list[AdminFeedPostMediaRow]]
    counts: AdminPostCounts

