from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .analysis import JobMatchResult
from .domain import Job, JobSearchSpec, StoredJob, StoredJobAnalysis


class JobCollector(Protocol):
    def collect(self, *, spec: JobSearchSpec) -> Sequence[Job]:
        """Collect raw jobs for the given search spec (may include duplicates)."""


class JobAnalyzer(Protocol):
    def analyze(self, *, spec: JobSearchSpec, job: Job) -> JobMatchResult:
        """Analyze a single job and return a structured match result."""


class JobRepository(Protocol):
    def upsert_jobs(self, *, spec: JobSearchSpec, jobs: Sequence[Job]) -> Sequence[StoredJob]:
        """Upsert jobs and return stored handles (must preserve stable source_key)."""

    def upsert_job_analyses(
        self, *, spec: JobSearchSpec, analyses: Sequence[StoredJobAnalysis]
    ) -> None:
        """Upsert analyses for (job_search_id, job_id) pairs."""

