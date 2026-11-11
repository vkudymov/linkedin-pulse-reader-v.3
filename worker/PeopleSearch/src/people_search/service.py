from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .domain import PeopleSearchSpec, PersonProfile, StoredPerson, StoredPersonAnalysis
from .ports import PeopleAnalyzer, PeopleCollector, PeopleRepository


@dataclass(frozen=True, slots=True)
class PeopleSearchResult:
    collected: int
    unique: int
    analyzed: int
    matched: int
    enriched: int
    errors: int


class PeopleSearchService:
    def __init__(
        self,
        *,
        collector: PeopleCollector,
        analyzer: PeopleAnalyzer,
        repository: PeopleRepository,
    ) -> None:
        self._collector = collector
        self._analyzer = analyzer
        self._repository = repository

    def run(self, *, spec: PeopleSearchSpec) -> PeopleSearchResult:
        people = list(self._collector.collect(spec=spec))
        collected = len(people)

        unique_by_key: dict[str, PersonProfile] = {}
        for p in people:
            if p.source_key and p.source_key not in unique_by_key:
                unique_by_key[p.source_key] = p
        unique_people = list(unique_by_key.values())

        stored = list(self._repository.upsert_people(spec=spec, people=unique_people))
        stored_by_key = {s.source_key: s for s in stored}

        analyzed = 0
        matched = 0
        enriched = 0
        errors = 0
        analyses: list[StoredPersonAnalysis] = []
        now = datetime.now(UTC)
        min_score = int(spec.min_score or 0)
        target_found = int(spec.target_found or 0)
        shortlist_floor = max(0, min_score - 20)
        enrich_cap = max(1, target_found * 3)

        for person in unique_people:
            stored_person = stored_by_key.get(person.source_key)
            if stored_person is None:
                errors += 1
                continue
            try:
                card_result = self._analyzer.analyze(spec=spec, person=person)
                analyzed += 1
                current = person
                stage: str = "card"
                result = card_result
                if (
                    enriched < enrich_cap
                    and int(card_result.score) >= shortlist_floor
                    and matched < target_found
                ):
                    try:
                        current = self._collector.enrich(person=person)
                        enriched += 1
                        stage = "profile"
                        result = self._analyzer.analyze(spec=spec, person=current)
                        analyzed += 1
                        self._repository.upsert_people(spec=spec, people=[current])
                    except Exception as e:  # noqa: BLE001
                        errors += 1
                        analyses.append(
                            StoredPersonAnalysis(
                                search_id=spec.people_search_id,
                                person_id=stored_person.person_id,
                                analyzed_at=now,
                                match=bool(card_result.match and int(card_result.score) >= min_score),
                                score=int(card_result.score),
                                reason=card_result.reason,
                                matched_requirements=card_result.matched_requirements,
                                missing_requirements=card_result.missing_requirements,
                                red_flags=card_result.red_flags,
                                stage="card",
                                raw_payload=card_result.raw_payload,
                                error=f"enrich failed: {e}",
                            )
                        )
                        if bool(card_result.match and int(card_result.score) >= min_score):
                            matched += 1
                            if matched >= target_found:
                                break
                        continue

                effective_match = bool(result.match and int(result.score) >= min_score)
                if effective_match:
                    matched += 1
                analyses.append(
                    StoredPersonAnalysis(
                        search_id=spec.people_search_id,
                        person_id=stored_person.person_id,
                        analyzed_at=now,
                        match=effective_match,
                        score=int(result.score),
                        reason=result.reason,
                        matched_requirements=result.matched_requirements,
                        missing_requirements=result.missing_requirements,
                        red_flags=result.red_flags,
                        stage=stage,  # type: ignore[arg-type]
                        raw_payload=result.raw_payload,
                        error=None,
                    )
                )
                if matched >= target_found:
                    break
            except Exception as e:  # noqa: BLE001
                errors += 1
                analyses.append(
                    StoredPersonAnalysis(
                        search_id=spec.people_search_id,
                        person_id=stored_person.person_id,
                        analyzed_at=now,
                        match=False,
                        score=0,
                        reason="",
                        matched_requirements=(),
                        missing_requirements=(),
                        red_flags=(),
                        stage="card",
                        raw_payload=None,
                        error=str(e),
                    )
                )

        self._repository.upsert_people_analyses(spec=spec, analyses=analyses)
        return PeopleSearchResult(
            collected=collected,
            unique=len(unique_people),
            analyzed=analyzed,
            matched=matched,
            enriched=enriched,
            errors=errors,
        )
