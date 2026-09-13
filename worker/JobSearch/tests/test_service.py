from __future__ import annotations

from dataclasses import dataclass

from job_search.analysis import JobMatchResult
from job_search.domain import Job, JobSearchSpec, StoredJob, StoredJobAnalysis
from job_search.service import JobSearchService


@dataclass
class FakeCollector:
    jobs: list[Job]

    def collect(self, *, spec: JobSearchSpec) -> list[Job]:
        return list(self.jobs)


@dataclass
class FakeAnalyzer:
    def analyze(self, *, spec: JobSearchSpec, job: Job) -> JobMatchResult:
        return JobMatchResult(
            match=True,
            score=80,
            reason="ok",
            matched_requirements=("python",),
            missing_requirements=(),
            red_flags=(),
            raw_payload={"match": True, "score": 80},
        )


class FakeRepo:
    def __init__(self) -> None:
        self.saved_jobs: list[Job] = []
        self.saved_analyses: list[StoredJobAnalysis] = []

    def upsert_jobs(self, *, spec: JobSearchSpec, jobs: list[Job]) -> list[StoredJob]:
        self.saved_jobs.extend(jobs)
        return [
            StoredJob(job_id=f"id:{j.source_key}", source_key=j.source_key, job_url=j.job_url)
            for j in jobs
        ]

    def upsert_job_analyses(
        self, *, spec: JobSearchSpec, analyses: list[StoredJobAnalysis]
    ) -> None:
        self.saved_analyses.extend(analyses)


def test_service_dedupes_by_source_key() -> None:
    spec = JobSearchSpec(
        job_search_id="s1",
        title="Prompt Engineer",
        search_query="Prompt Engineer",
        location="Europe",
        filter_prompt="<<<JOB_TEXT>>>",
        limit=25,
    )
    j1 = Job(source_key="job:1", job_url="https://x/jobs/view/1", title="A")
    j2 = Job(source_key="job:1", job_url="https://x/jobs/view/1?trk=dup", title="A-dup")

    repo = FakeRepo()
    svc = JobSearchService(
        collector=FakeCollector([j1, j2]),
        analyzer=FakeAnalyzer(),
        repository=repo,
    )
    r = svc.run(spec=spec)

    assert r.collected == 2
    assert r.unique == 1
    assert len(repo.saved_jobs) == 1
    assert len(repo.saved_analyses) == 1
    assert repo.saved_analyses[0].job_search_id == "s1"

