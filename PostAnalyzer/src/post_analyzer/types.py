from __future__ import annotations

from typing import Any, TypedDict


class PostInput(TypedDict, total=False):
    text: str
    post_url: str
    # Any extra keys are allowed but ignored by the analyzer.


class AnalysisItem(TypedDict):
    post_url: str
    is_relevant: bool
    comment: str | None
    error: str | None


PostInputList = list[dict[str, Any]]
AnalysisResult = list[AnalysisItem]

