from .analysis import JobMatchResult, parse_job_match_json
from .domain import Job, JobSearchSpec, StoredJob
from .ports import JobAnalyzer, JobCollector, JobRepository
from .service import JobSearchResult, JobSearchService

__all__ = [
    "Job",
    "JobAnalyzer",
    "JobCollector",
    "JobMatchResult",
    "JobRepository",
    "JobSearchResult",
    "JobSearchService",
    "JobSearchSpec",
    "StoredJob",
    "parse_job_match_json",
]

