from __future__ import annotations

import json

from post_analyzer.llm_factory import FakeLLMClient


def test_fake_llm_returns_job_schema_for_job_prompt() -> None:
    raw = FakeLLMClient().complete(
        system=None,
        user="Return strict JSON only (match/score/reason/requirements).\nTitle: Engineer",
    )
    payload = json.loads(raw)
    assert payload["match"] is False
    assert payload["score"] == 0
    assert isinstance(payload["reason"], str) and payload["reason"]
    assert payload["matched_requirements"] == []
    assert payload["missing_requirements"] == []
    assert payload["red_flags"] == []


def test_fake_llm_job_schema_wins_over_relevant_word_in_description() -> None:
    raw = FakeLLMClient().complete(
        system=None,
        user=(
            "Return ONLY valid JSON with matched_requirements.\n"
            "Description: this role is relevant for senior engineers."
        ),
    )
    payload = json.loads(raw)
    assert "match" in payload
    assert "relevant" not in payload


def test_fake_llm_keeps_post_relevance_heuristic() -> None:
    raw = FakeLLMClient().complete(
        system=None,
        user='Reply with strict json only: {"relevant": true|false}',
    )
    assert json.loads(raw) == {"relevant": False}
