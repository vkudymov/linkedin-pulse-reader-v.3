from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from ..config import PostAnalyzerConfig
from ..llm import LLMClient


@dataclass(frozen=True, slots=True)
class RelevanceResult:
    relevant: bool
    error: str | None = None
    score: int | None = None
    content_type: str | None = None
    main_topics: list[str] | None = None
    reason: str | None = None
    selection_reason: str | None = None
    analysis: dict[str, Any] | None = None


class RelevanceFilter:
    def __init__(self, *, llm_client: LLMClient, config: PostAnalyzerConfig) -> None:
        self._llm_client = llm_client
        self._config = config

    def check(self, post: Mapping[str, Any]) -> RelevanceResult:
        text = post.get("text")
        post_url = post.get("post_url")

        if not isinstance(text, str) or not text.strip():
            return RelevanceResult(relevant=False, error="Post is missing non-empty 'text'.")
        if not isinstance(post_url, str) or not post_url.strip():
            return RelevanceResult(relevant=False, error="Post is missing non-empty 'post_url'.")

        try:
            raw = self._llm_client.complete(
                system=self._config.relevance_system_prompt,
                user=self._config.format_relevance_user(text=text, post_url=post_url),
            )
        except Exception as e:  # noqa: BLE001 - library boundary: normalize to string
            return RelevanceResult(relevant=False, error=f"LLM relevance check failed: {e}")

        try:
            return _parse_relevance_result(raw)
        except Exception as e:
            preview = (raw or "").strip().replace("\n", " ")
            if len(preview) > 200:
                preview = f"{preview[:200]}…"
            return RelevanceResult(
                relevant=False,
                error=f"Invalid relevance response: {e}. Raw: {preview!r}",
            )


def _parse_relevance_result(raw: str) -> RelevanceResult:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:  # pragma: no cover
        raise ValueError("Expected strict JSON.") from e

    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")

    value = payload.get("relevant", payload.get("is_relevant"))
    if isinstance(value, bool):
        reason = payload.get("reason")
        selection_reason = payload.get("selection_reason")
        return RelevanceResult(
            relevant=value,
            error=None,
            reason=reason if isinstance(reason, str) else None,
            selection_reason=selection_reason if isinstance(selection_reason, str) else None,
            analysis=payload,
        )

    raise ValueError("Expected boolean field 'relevant' (or 'is_relevant').")

