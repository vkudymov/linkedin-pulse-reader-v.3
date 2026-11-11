from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .analysis import PeopleMatchResult
from .domain import PeopleSearchSpec, PersonProfile, StoredPerson, StoredPersonAnalysis


class PeopleCollector(Protocol):
    def collect(self, *, spec: PeopleSearchSpec) -> Sequence[PersonProfile]:
        """Collect people cards for the given search spec (may include duplicates)."""

    def enrich(self, *, person: PersonProfile) -> PersonProfile:
        """Open the profile and fill about/skills/experience/education."""


class PeopleAnalyzer(Protocol):
    def analyze(self, *, spec: PeopleSearchSpec, person: PersonProfile) -> PeopleMatchResult:
        """Analyze a person card or enriched profile."""


class PeopleRepository(Protocol):
    def upsert_people(
        self, *, spec: PeopleSearchSpec, people: Sequence[PersonProfile]
    ) -> Sequence[StoredPerson]:
        """Upsert people and return stored handles (must preserve stable source_key)."""

    def upsert_people_analyses(
        self, *, spec: PeopleSearchSpec, analyses: Sequence[StoredPersonAnalysis]
    ) -> None:
        """Upsert analyses for (search_id, person_id) pairs."""
