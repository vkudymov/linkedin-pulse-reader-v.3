"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_jobs.parsing.job_insights import (
    JobInsights,
    classify_job_insights,
    normalize_insight_key,
)

__all__ = ['JobInsights', 'classify_job_insights', 'normalize_insight_key']
