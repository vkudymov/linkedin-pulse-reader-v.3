from __future__ import annotations

from dataclasses import dataclass

from people_search.dedupe import compute_source_key
from people_search.domain import PeopleSearchSpec, PersonProfile


def _as_tuple_str(values: object) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, (list, tuple)):
        return tuple(str(x).strip() for x in values if str(x).strip())
    return ()


def _as_tuple_maps(values: object) -> tuple[dict, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    out: list[dict] = []
    for item in values:
        if isinstance(item, dict):
            out.append(dict(item))
    return tuple(out)


def _from_linkedin_person(p: object) -> PersonProfile | None:
    profile_url = str(getattr(p, "profile_url", None) or "").strip()
    public_id = str(getattr(p, "public_id", None) or "").strip() or None
    if not profile_url:
        return None
    source_key = compute_source_key(profile_url=profile_url, public_id=public_id)
    return PersonProfile(
        source_key=source_key,
        profile_url=profile_url,
        public_id=public_id,
        full_name=getattr(p, "full_name", None) or None,
        avatar_url=getattr(p, "avatar_url", None) or None,
        headline=getattr(p, "headline", None) or None,
        location=getattr(p, "location", None) or None,
        connection_degree=getattr(p, "connection_degree", None) or None,
        snippet=getattr(p, "snippet", None) or None,
        about=getattr(p, "about", None) or None,
        skills=_as_tuple_str(getattr(p, "skills", ())),
        current_company=getattr(p, "current_company", None) or None,
        experience=_as_tuple_maps(getattr(p, "experience", ())),
        education=_as_tuple_maps(getattr(p, "education", ())),
        raw={
            "public_id": public_id,
            "profile_url": profile_url,
            "full_name": getattr(p, "full_name", None),
            "avatar_url": getattr(p, "avatar_url", None),
            "headline": getattr(p, "headline", None),
            "location": getattr(p, "location", None),
        },
    )


@dataclass(frozen=True, slots=True)
class LinkedInPeopleCollector:
    """Adapter: LinkedInSession + PeopleSearch -> PersonProfile list."""

    session: object

    def collect(self, *, spec: PeopleSearchSpec) -> list[PersonProfile]:
        from linkedin_search_people import PeopleSearch  # type: ignore[import-untyped]

        raw = PeopleSearch(self.session).fetch(
            keywords=spec.query,
            limit=spec.limit,
            filters=spec.filters,
        )
        out: list[PersonProfile] = []
        for p in raw:
            mapped = _from_linkedin_person(p)
            if mapped is not None:
                out.append(mapped)
        return out

    def enrich(self, *, person: PersonProfile) -> PersonProfile:
        from linkedin_search_people import PeopleSearch  # type: ignore[import-untyped]

        enriched = PeopleSearch(self.session).enrich(person.profile_url)
        mapped = _from_linkedin_person(enriched)
        if mapped is None:
            return person
        return PersonProfile(
            source_key=person.source_key,
            profile_url=mapped.profile_url or person.profile_url,
            public_id=mapped.public_id or person.public_id,
            full_name=mapped.full_name or person.full_name,
            avatar_url=mapped.avatar_url or person.avatar_url,
            headline=mapped.headline or person.headline,
            location=mapped.location or person.location,
            connection_degree=mapped.connection_degree or person.connection_degree,
            snippet=person.snippet,
            about=mapped.about or person.about,
            skills=mapped.skills or person.skills,
            current_company=mapped.current_company or person.current_company,
            experience=mapped.experience or person.experience,
            education=mapped.education or person.education,
            raw=mapped.raw or person.raw,
        )
