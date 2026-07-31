from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LoginMethodStr = Literal["email", "google", "apple"]
LoginStatusStr = Literal[
    "pending",
    "awaiting_user",
    "checkpoint",
    "completed",
    "failed",
    "cancelled",
]


class LoginStartRequest(BaseModel):
    method: LoginMethodStr = "email"
    identifier: str | None = Field(default=None, description="Email or phone (for method=email).")
    password: str | None = Field(default=None, description="Password (for method=email).")
    label: str | None = Field(default=None, description="Optional label for linkedin_accounts row.")


class LoginSessionResponse(BaseModel):
    session_id: str
    status: LoginStatusStr
    message: str | None = None
    linkedin_account_id: str | None = None

