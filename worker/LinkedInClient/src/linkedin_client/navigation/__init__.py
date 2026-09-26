"""Compatibility re-export of navigators."""

from linkedin_search_jobs.navigation.jobs import JobsNavigator
from linkedin_search_posts.navigation.feed import FeedNavigator

__all__ = ["FeedNavigator", "JobsNavigator"]
