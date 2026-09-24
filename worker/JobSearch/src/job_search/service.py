from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .domain import Job, JobSearchSpec, StoredJobAnalysis
from .ports import JobAnalyzer, JobCollector, JobRepository


@dataclass(frozen=True, slots=True)
class JobSearchResult:
    collected: int
    unique: int
    analyzed: int
    matched: int
    errors: int
    report_items: tuple[dict[str, object], ...] = ()


class JobSearchService:
    def __init__(
        self,
        *,
        collector: JobCollector,
        analyzer: JobAnalyzer,
        repository: JobRepository,
    ) -> None:
        self._collector = collector
        self._analyzer = analyzer
        self._repository = repository

    def run(self, *, spec: JobSearchSpec) -> JobSearchResult:
        jobs = list(self._collector.collect(spec=spec))
        collected = len(jobs)

        # Dedup happens by stable job.source_key.
        unique_by_key: dict[str, Job] = {}
        for j in jobs:
            if j.source_key and j.source_key not in unique_by_key:
                unique_by_key[j.source_key] = j
        unique_jobs = list(unique_by_key.values())

        stored = list(self._repository.upsert_jobs(spec=spec, jobs=unique_jobs))
        stored_by_key = {s.source_key: s for s in stored}

        analyzed = 0
        matched = 0
        errors = 0
        analyses: list[StoredJobAnalysis] = []
        report_items: list[dict[str, object]] = []
        analyzed_keys: set[str] = set()
        now = datetime.now(UTC)

        for job in unique_jobs:
            stored_job = stored_by_key.get(job.source_key)
            if stored_job is None:
                # Repository contract violation; count as error but continue.
                errors += 1
                continue

            try:
                r = self._analyzer.analyze(spec=spec, job=job)
                analyzed += 1
                analyzed_keys.add(job.source_key)
                effective_match = bool(r.match and int(r.score) >= int(spec.min_score or 0))
                if effective_match:
                    matched += 1
                report_items.append(
                    {
                        "analyzed": True,
                        "match": bool(effective_match),
                        "score": int(r.score),
                        "reason": r.reason,
                        "matched_requirements": list(r.matched_requirements),
                        "missing_requirements": list(r.missing_requirements),
                        "red_flags": list(r.red_flags),
                        "job": {
                            "job_url": job.job_url,
                            "title": job.title,
                            "company": job.company,
                            "location": job.location,
                            "description": job.description,
                        },
                    }
                )
                analyses.append(
                    StoredJobAnalysis(
                        job_search_id=spec.job_search_id,
                        job_id=stored_job.job_id,
                        analyzed_at=now,
                        match=effective_match,
                        score=int(r.score),
                        reason=r.reason,
                        matched_requirements=r.matched_requirements,
                        missing_requirements=r.missing_requirements,
                        red_flags=r.red_flags,
                        raw_payload=r.raw_payload,
                        error=None,
                    ),
                )
                if matched >= int(spec.target_found or 0):
                    break
            except Exception as e:  # noqa: BLE001 - boundary normalize to string
                errors += 1
                analyses.append(
                    StoredJobAnalysis(
                        job_search_id=spec.job_search_id,
                        job_id=stored_job.job_id,
                        analyzed_at=now,
                        match=False,
                        score=0,
                        reason="",
                        matched_requirements=(),
                        missing_requirements=(),
                        red_flags=(),
                        raw_payload=None,
                        error=str(e),
                    ),
                )

        # Add not-analyzed jobs (early-stop) to the report payload.
        for job in unique_jobs:
            if not job.source_key or job.source_key in analyzed_keys:
                continue
            report_items.append(
                {
                    "analyzed": False,
                    "match": None,
                    "score": None,
                    "reason": "not analyzed",
                    "matched_requirements": [],
                    "missing_requirements": [],
                    "red_flags": [],
                    "job": {
                        "job_url": job.job_url,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "description": job.description,
                    },
                }
            )

        self._repository.upsert_job_analyses(spec=spec, analyses=analyses)

        return JobSearchResult(
            collected=collected,
            unique=len(unique_jobs),
            analyzed=analyzed,
            matched=matched,
            errors=errors,
            report_items=tuple(report_items),
        )

