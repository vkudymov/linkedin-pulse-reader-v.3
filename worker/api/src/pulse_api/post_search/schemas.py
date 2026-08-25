from __future__ import annotations

from pydantic import BaseModel, Field


class PostSearchStartRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=200)
    account_label: str | None = None


class PostSearchRunResponse(BaseModel):
    session_id: str
    status: str
    message: str | None = None

