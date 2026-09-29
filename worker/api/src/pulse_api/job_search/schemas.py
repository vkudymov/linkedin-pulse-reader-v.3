from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JobSearchStartRequest(BaseModel):
    job_search_id: str = Field(..., min_length=1)
    limit: int | None = Field(default=None, ge=1, le=500)
    account_label: str | None = None


class JobSearchRunResponse(BaseModel):
    session_id: str
    status: Literal["running", "done", "error", "lost"]
    message: str | None = None

