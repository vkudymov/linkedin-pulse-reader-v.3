"""LinkedIn job search on top of linkedin-search-core."""

from .models.job import Job
from .search import JobSearch

__all__ = ["Job", "JobSearch"]
