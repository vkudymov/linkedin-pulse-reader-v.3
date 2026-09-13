from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class JobMatchResult:
    match: bool
    score: int
    reason: str
    matched_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    red_flags: tuple[str, ...]
    raw_payload: Mapping[str, Any] | None = None


def _as_str_list(v: Any) -> tuple[str, ...]:
    if v is None:
        return ()
    if not isinstance(v, list):
        raise ValueError("expected list")
    out: list[str] = []
    for item in v:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return tuple(out)


def parse_job_match_json(text: str) -> JobMatchResult:
    """
    Parse LLM JSON response into the structured contract:
    {match, score, reason, matched_requirements, missing_requirements, red_flags}
    """

    try:
        payload = json.loads(text)
    except Exception as e:  # noqa: BLE001 - boundary normalize to ValueError
        raise ValueError(f"invalid json: {e}") from e

    if not isinstance(payload, dict):
        raise ValueError("expected JSON object")

    match = bool(payload.get("match"))
    score_raw = payload.get("score")
    if not isinstance(score_raw, int):
        raise ValueError("score must be int")
    score = max(0, min(100, int(score_raw)))

    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be non-empty string")

    try:
        matched = _as_str_list(payload.get("matched_requirements"))
        missing = _as_str_list(payload.get("missing_requirements"))
        red_flags = _as_str_list(payload.get("red_flags"))
    except ValueError as e:
        raise ValueError(f"invalid list field: {e}") from e

    return JobMatchResult(
        match=match,
        score=score,
        reason=reason.strip(),
        matched_requirements=matched,
        missing_requirements=missing,
        red_flags=red_flags,
        raw_payload=payload,
    )

