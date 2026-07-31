from __future__ import annotations

import json
import re
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
    raw_s = raw or ""
    json_text = _coerce_json_text(raw_s)

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as e:
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


_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*([\s\S]*?)\s*```\s*$")


def _coerce_json_text(raw: str) -> str:
    """
    Accept strict JSON wrapped in Markdown fences or surrounded by minor extra text.

    We still only parse a single JSON object. This is a tolerance layer for LLM outputs,
    while keeping the downstream schema checks strict.
    """
    s = (raw or "").strip()
    if not s:
        return s

    if (m := _FENCE_RE.match(s)) is not None:
        s = (m.group(1) or "").strip()

    # Some models return: ```json { ... } ``` on one line with extra spaces.
    if s.startswith("```") and "```" in s[3:]:
        first = s.find("```")
        last = s.rfind("```")
        if last > first:
            inner = s[first + 3 : last]
            # Drop possible language tag at start of inner.
            inner = inner.lstrip()
            if "\n" in inner:
                first_line, rest = inner.split("\n", 1)
                if len(first_line) <= 16 and all(ch.isalnum() or ch in "-_" for ch in first_line.strip()):
                    inner = rest
            s = inner.strip()

    # If there's still extra text, extract the first JSON object by brace matching.
    extracted = _extract_first_json_object(s)
    return extracted if extracted is not None else s


def _extract_first_json_object(s: str) -> str | None:
    start = s.find("{")
    if start < 0:
        return None

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1].strip()
    return None

