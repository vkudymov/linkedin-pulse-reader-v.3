from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from people_search.domain import PeopleSearchSpec, PersonProfile, StoredPerson, StoredPersonAnalysis


@dataclass(frozen=True, slots=True)
class StoragePeopleRepository:
    storage: object
    user_id: str
    linkedin_account_id: str

    def upsert_people(self, *, spec: PeopleSearchSpec, people: list[PersonProfile]) -> list[StoredPerson]:
        from storage.facade import PulseStorage  # type: ignore[import-untyped]

        if not isinstance(self.storage, PulseStorage):  # pragma: no cover
            raise TypeError("StoragePeopleRepository.storage must be storage.facade.PulseStorage")

        payload = [
            {
                "source_key": p.source_key,
                "profile_url": p.profile_url,
                "public_id": p.public_id,
                "full_name": p.full_name,
                "avatar_url": p.avatar_url,
                "headline": p.headline,
                "location": p.location,
                "connection_degree": p.connection_degree,
                "about": p.about,
                "skills": list(p.skills),
                "current_company": p.current_company,
                "experience": [dict(x) for x in p.experience],
                "education": [dict(x) for x in p.education],
                "raw_extra": dict(p.raw) if isinstance(p.raw, dict) else None,
            }
            for p in people
        ]
        rows = self.storage.people.upsert_people(
            user_id=self.user_id,
            linkedin_account_id=self.linkedin_account_id,
            people=payload,
        )
        out: list[StoredPerson] = []
        for r in rows:
            sid = r.get("id")
            skey = r.get("source_key")
            url = r.get("profile_url")
            if isinstance(sid, str) and isinstance(skey, str) and isinstance(url, str):
                out.append(StoredPerson(person_id=sid, source_key=skey, profile_url=url))
        return out

    def upsert_people_analyses(
        self, *, spec: PeopleSearchSpec, analyses: list[StoredPersonAnalysis]
    ) -> None:
        from storage.facade import PulseStorage  # type: ignore[import-untyped]

        if not isinstance(self.storage, PulseStorage):  # pragma: no cover
            raise TypeError("StoragePeopleRepository.storage must be storage.facade.PulseStorage")

        now = datetime.now(UTC).isoformat()
        payload = [
            {
                "search_id": a.search_id,
                "person_id": a.person_id,
                "analyzed_at": a.analyzed_at.isoformat(),
                "match": bool(a.match),
                "score": int(a.score),
                "reason": a.reason,
                "matched_requirements": list(a.matched_requirements),
                "missing_requirements": list(a.missing_requirements),
                "red_flags": list(a.red_flags),
                "stage": a.stage,
                "raw_payload": dict(a.raw_payload) if isinstance(a.raw_payload, dict) else None,
                "error": a.error,
                "updated_at": now,
            }
            for a in analyses
        ]
        self.storage.people_analyses.upsert_analyses(analyses=payload)
