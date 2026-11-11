from __future__ import annotations

from dataclasses import dataclass

import pytest

from people_search.adapters.llm_people_analyzer import LlmPeopleAnalyzer
from people_search.domain import PeopleSearchSpec, PersonProfile


@dataclass
class FakeLLM:
    reply: str

    def complete(self, *, system: str | None, user: str) -> str:  # noqa: ARG002
        return self.reply


def test_replaces_marker_and_parses() -> None:
    spec = PeopleSearchSpec(
        people_search_id="s1",
        title="t",
        query="q",
        prompt="Check:\n<<<PROFILE_TEXT>>>",
    )
    person = PersonProfile(
        source_key="in:a",
        profile_url="https://www.linkedin.com/in/a",
        full_name="Ada",
        headline="ABAP developer",
    )
    llm = FakeLLM(
        reply='{"match":true,"score":88,"reason":"ok","matched_requirements":["ABAP"],"missing_requirements":[],"red_flags":[]}',
    )
    r = LlmPeopleAnalyzer(llm_client=llm).analyze(spec=spec, person=person)
    assert r.match is True
    assert r.score == 88


def test_requires_marker() -> None:
    spec = PeopleSearchSpec(people_search_id="s1", title="t", query="q", prompt="no marker")
    person = PersonProfile(source_key="in:a", profile_url="https://www.linkedin.com/in/a")
    with pytest.raises(ValueError):
        LlmPeopleAnalyzer(llm_client=FakeLLM(reply="{}")).analyze(spec=spec, person=person)
