from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JobSearchStartRequest(BaseModel):
    job_search_id: str = Field(..., min_length=1)
    limit: int = Field(25, ge=1, le=200)
    account_label: str | None = None


class JobSearchRunResponse(BaseModel):
    session_id: str
    status: Literal["running", "done", "error"]
    message: str | None = None

