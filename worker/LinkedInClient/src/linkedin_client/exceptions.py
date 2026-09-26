"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_core.exceptions import (
    LinkedInClientError,
    BrowserLifecycleError,
    CookieFormatError,
    LoginRequiredError,
    LoginTimeoutError,
    LoginCheckpointError,
    LoginCancelledError,
    FeedLoadError,
    PostParseError,
)

__all__ = ['LinkedInClientError', 'BrowserLifecycleError', 'CookieFormatError', 'LoginRequiredError', 'LoginTimeoutError', 'LoginCheckpointError', 'LoginCancelledError', 'FeedLoadError', 'PostParseError']
