"""Compatibility re-export of loading helpers."""

from linkedin_search_core.loading.scroller import HumanScroller, ScrollConfig
from linkedin_search_jobs.loading.jobs_waiter import JobsWaiter
from linkedin_search_posts.loading.waiter import FeedWaiter

__all__ = ["FeedWaiter", "HumanScroller", "JobsWaiter", "ScrollConfig"]
