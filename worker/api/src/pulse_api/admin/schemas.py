from __future__ import annotations

from datetime import date, datetime

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

