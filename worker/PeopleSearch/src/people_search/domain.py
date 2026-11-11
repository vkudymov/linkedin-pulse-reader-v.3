from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

AnalysisStage = Literal["card", "profile"]


@dataclass(frozen=True, slots=True)
class PersonProfile:
    source_key: str
    profile_url: str
    public_id: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None
    headline: str | None = None
    location: str | None = None
    connection_degree: str | None = None
    snippet: str | None = None
    about: str | None = None
    skills: tuple[str, ...] = ()
    current_company: str | None = None
    experience: tuple[Mapping[str, Any], ...] = ()
    education: tuple[Mapping[str, Any], ...] = ()
    raw: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PeopleSearchSpec:
    """`prompt` must contain the marker <<<PROFILE_TEXT>>> (validated at the UI/API boundary)."""

    people_search_id: str
    title: str
    query: str
    prompt: str
    limit: int = 25
    min_score: int = 0
    target_found: int = 10
    filters: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class StoredPerson:
    person_id: str
    source_key: str
    profile_url: str


@dataclass(frozen=True, slots=True)
class StoredPersonAnalysis:
    search_id: str
    person_id: str
    analyzed_at: datetime
    match: bool
    score: int
    reason: str
    matched_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    red_flags: tuple[str, ...]
    stage: AnalysisStage = "card"
    raw_payload: Mapping[str, Any] | None = None
    error: str | None = None
