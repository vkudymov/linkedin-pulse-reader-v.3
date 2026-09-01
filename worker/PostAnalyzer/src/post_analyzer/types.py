from __future__ import annotations

from typing import TypedDict


class AnalysisItem(TypedDict):
    post_url: str
    is_relevant: bool
    comment: str | None
    error: str | None

