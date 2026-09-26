"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_jobs.navigation.job_search_url import (
    resolve_job_filters,
    compose_job_keywords,
    build_jobs_search_query,
    build_jobs_search_url,
)

__all__ = ['resolve_job_filters', 'compose_job_keywords', 'build_jobs_search_query', 'build_jobs_search_url']
