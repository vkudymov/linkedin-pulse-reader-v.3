from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from job_search.domain import Job, JobSearchSpec, StoredJob, StoredJobAnalysis


@dataclass(frozen=True, slots=True)
class StorageJobRepository:
    """
    Adapter: Storage (Supabase) -> JobSearch repository port.

    Stores:
    - jobs: unique per (user_id, source_key)
    - job_analyses: unique per (job_search_id, job_id)
    """

    storage: object
    user_id: str
    linkedin_account_id: str

    def upsert_jobs(self, *, spec: JobSearchSpec, jobs: list[Job]) -> list[StoredJob]:
        from storage.facade import PulseStorage  # type: ignore[import-untyped]

        if not isinstance(self.storage, PulseStorage):  # pragma: no cover
            raise TypeError("StorageJobRepository.storage must be storage.facade.PulseStorage")

        payload = [
            {
                "source_key": j.source_key,
                "job_url": j.job_url,
                "linkedin_job_id": j.raw.get("job_id") if isinstance(j.raw, dict) else None,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "description": j.description,
                "raw_extra": dict(j.raw) if isinstance(j.raw, dict) else None,
            }
            for j in jobs
        ]
        rows = self.storage.jobs.upsert_jobs(
            user_id=self.user_id,
            linkedin_account_id=self.linkedin_account_id,
            jobs=payload,
        )

        out: list[StoredJob] = []
        for r in rows:
            sid = r.get("id")
            skey = r.get("source_key")
            url = r.get("job_url")
            if isinstance(sid, str) and isinstance(skey, str) and isinstance(url, str):
                out.append(StoredJob(job_id=sid, source_key=skey, job_url=url))
        return out

    def upsert_job_analyses(self, *, spec: JobSearchSpec, analyses: list[StoredJobAnalysis]) -> None:
        from storage.facade import PulseStorage  # type: ignore[import-untyped]

        if not isinstance(self.storage, PulseStorage):  # pragma: no cover
            raise TypeError("StorageJobRepository.storage must be storage.facade.PulseStorage")

        now = datetime.now(UTC).isoformat()
        payload = [
            {
                "job_search_id": a.job_search_id,
                "job_id": a.job_id,
                "analyzed_at": a.analyzed_at.isoformat(),
                "match": bool(a.match),
                "score": int(a.score),
                "reason": a.reason,
                "matched_requirements": list(a.matched_requirements),
                "missing_requirements": list(a.missing_requirements),
                "red_flags": list(a.red_flags),
                "raw_payload": dict(a.raw_payload) if isinstance(a.raw_payload, dict) else None,
                "error": a.error,
                "updated_at": now,
            }
            for a in analyses
        ]
        self.storage.job_analyses.upsert_analyses(analyses=payload)  # type: ignore[arg-type]

