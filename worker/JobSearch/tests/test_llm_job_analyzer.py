from __future__ import annotations

from dataclasses import dataclass

import pytest

from job_search.adapters.llm_job_analyzer import LlmJobAnalyzer
from job_search.domain import Job, JobSearchSpec


@dataclass
class FakeLLM:
    reply: str

    def complete(self, *, system: str | None, user: str) -> str:  # noqa: ARG002
        return self.reply


def test_llm_job_analyzer_replaces_marker_and_parses() -> None:
    spec = JobSearchSpec(
        job_search_id="s1",
        title="t",
        search_query="q",
        location=None,
        filter_prompt="Check:\n<<<JOB_TEXT>>>",
        limit=1,
    )
    job = Job(source_key="k", job_url="u", title="Engineer", description="Python")

    llm = FakeLLM(
        reply='{"match":true,"score":87,"reason":"ok","matched_requirements":[],"missing_requirements":[],"red_flags":[]}',
    )
    r = LlmJobAnalyzer(llm_client=llm).analyze(spec=spec, job=job)
    assert r.match is True
    assert r.score == 87


def test_llm_job_analyzer_requires_marker() -> None:
    spec = JobSearchSpec(
        job_search_id="s1",
        title="t",
        search_query="q",
        location=None,
        filter_prompt="no marker",
        limit=1,
    )
    job = Job(source_key="k", job_url="u", title="Engineer")
    llm = FakeLLM(reply="{}")
    with pytest.raises(ValueError):
        LlmJobAnalyzer(llm_client=llm).analyze(spec=spec, job=job)

