from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Person:
    """
    Best-effort LinkedIn people-search / profile model.

    Search cards usually fill public_id, profile_url, full_name, headline, location,
    connection_degree, snippet. Profile enrichment fills about, skills, experience, education.
    """

    public_id: str | None = None
    profile_url: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None
    headline: str | None = None
    location: str | None = None
    connection_degree: str | None = None
    snippet: str | None = None
    about: str | None = None
    skills: tuple[str, ...] = ()
    current_company: str | None = None
    experience: tuple[dict[str, Any], ...] = ()
    education: tuple[dict[str, Any], ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)
