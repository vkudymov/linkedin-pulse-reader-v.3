from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class AdminJobSearchRow(BaseModel):
    id: str
    user_id: str
    title: str
    search_query: str
    location: str | None = None
    filter_prompt: str
    status: str | None = None
    last_run_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminJobSearchUpdate(BaseModel):
    title: str | None = None
    search_query: str | None = None
    location: str | None = None
    filter_prompt: str | None = None
    status: str | None = None


class AdminPostSearchStartRequest(BaseModel):
    post_search_id: str | None = None
    limit: int = Field(default=10, ge=1, le=200)
    account_label: str | None = None


class AdminPostSearchRow(BaseModel):
    id: str
    user_id: str
    title: str
    status: str | None = None
    last_run_at: datetime | None = None
    created_at: datetime | None = None


class AdminSearchRunRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    kind: str
    post_search_id: str | None = None
    job_search_id: str | None = None
    search_title: str
    limit_count: int
    account_label: str | None = None
    search_query: str | None = None
    location: str | None = None
    linkedin_filters: dict[str, Any] | None = None
    search_prompt: str | None = None
    comment_prompt: str | None = None
    filter_prompt: str | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    fetched_count: int | None = None
    analyzed_count: int | None = None
    matched_count: int | None = None
    error: str | None = None
    session_id: str | None = None
    initiated_by: str
    admin_actor_id: str | None = None
    user_email: str | None = None
    user_full_name: str | None = None


class AdminSearchRunsListResponse(BaseModel):
    items: list[AdminSearchRunRow]
    total: int
    limit: int
    offset: int

