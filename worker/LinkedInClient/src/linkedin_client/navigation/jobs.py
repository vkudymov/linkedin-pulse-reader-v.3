"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_jobs.navigation.jobs import (
    JobsNavigator,
    normalize_location_text,
)

__all__ = ['JobsNavigator', 'normalize_location_text']
