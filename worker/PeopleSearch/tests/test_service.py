from __future__ import annotations

from dataclasses import dataclass, replace

from people_search.analysis import PeopleMatchResult
from people_search.domain import PeopleSearchSpec, PersonProfile, StoredPerson, StoredPersonAnalysis
from people_search.service import PeopleSearchService


@dataclass
class FakeCollector:
    people: list[PersonProfile]
    enrich_calls: int = 0

    def collect(self, *, spec: PeopleSearchSpec) -> list[PersonProfile]:
        return list(self.people)

    def enrich(self, *, person: PersonProfile) -> PersonProfile:
        self.enrich_calls += 1
        return replace(person, about="Enriched about", skills=("ABAP", "HANA"))


@dataclass
class FakeAnalyzer:
    def analyze(self, *, spec: PeopleSearchSpec, person: PersonProfile) -> PeopleMatchResult:
        score = 80 if person.about else 55
        return PeopleMatchResult(
            match=score >= 70,
            score=score,
            reason="ok",
            matched_requirements=("ABAP",),
            missing_requirements=(),
            red_flags=(),
            raw_payload={"match": score >= 70, "score": score},
        )


class FakeRepo:
    def __init__(self) -> None:
        self.saved_people: list[PersonProfile] = []
        self.saved_analyses: list[StoredPersonAnalysis] = []

    def upsert_people(self, *, spec: PeopleSearchSpec, people: list[PersonProfile]) -> list[StoredPerson]:
        self.saved_people.extend(people)
        return [
            StoredPerson(person_id=f"id:{p.source_key}", source_key=p.source_key, profile_url=p.profile_url)
            for p in people
        ]

    def upsert_people_analyses(
        self, *, spec: PeopleSearchSpec, analyses: list[StoredPersonAnalysis]
    ) -> None:
        self.saved_analyses.extend(analyses)


def _spec(**kwargs: object) -> PeopleSearchSpec:
    base = dict(
        people_search_id="s1",
        title="SAP people",
        query="ABAP AND HANA",
        prompt="<<<PROFILE_TEXT>>>",
        limit=25,
        min_score=70,
        target_found=1,
    )
    base.update(kwargs)
    return PeopleSearchSpec(**base)  # type: ignore[arg-type]


def test_service_dedupes_and_enriches_shortlist() -> None:
    p1 = PersonProfile(source_key="in:a", profile_url="https://www.linkedin.com/in/a", full_name="A")
    p2 = PersonProfile(source_key="in:a", profile_url="https://www.linkedin.com/in/a?trk=x", full_name="A-dup")
    collector = FakeCollector([p1, p2])
    repo = FakeRepo()
    svc = PeopleSearchService(collector=collector, analyzer=FakeAnalyzer(), repository=repo)
    r = svc.run(spec=_spec())
    assert r.collected == 2
    assert r.unique == 1
    assert r.enriched == 1
    assert r.matched == 1
    assert collector.enrich_calls == 1
    assert any(a.stage == "profile" for a in repo.saved_analyses)
