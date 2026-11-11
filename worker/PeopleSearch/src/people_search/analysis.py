from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PeopleMatchResult:
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


def parse_people_match_json(text: str) -> PeopleMatchResult:
    try:
        payload = json.loads(text)
    except Exception as e:  # noqa: BLE001
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

    return PeopleMatchResult(
        match=match,
        score=score,
        reason=reason.strip(),
        matched_requirements=matched,
        missing_requirements=missing,
        red_flags=red_flags,
        raw_payload=payload,
    )


def match_result_to_payload(result: PeopleMatchResult) -> dict[str, Any]:
    return {
        "match": bool(result.match),
        "score": int(result.score),
        "reason": result.reason,
        "matched_requirements": list(result.matched_requirements),
        "missing_requirements": list(result.missing_requirements),
        "red_flags": list(result.red_flags),
        "raw_payload": dict(result.raw_payload) if isinstance(result.raw_payload, dict) else None,
    }
