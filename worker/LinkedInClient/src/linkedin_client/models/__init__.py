"""Compatibility re-export of models."""

from linkedin_search_core.models.user import UserIdentity
from linkedin_search_jobs.models.job import Job
from linkedin_search_posts.models.post import Author, Post

__all__ = ["Author", "Job", "Post", "UserIdentity"]
