"""Compatibility re-export of parsers."""

from linkedin_search_jobs.parsing.job_insights import JobInsights, classify_job_insights
from linkedin_search_jobs.parsing.job_parser import JobParser
from linkedin_search_posts.parsing.post_parser import PostParser

__all__ = ["JobInsights", "JobParser", "PostParser", "classify_job_insights"]
