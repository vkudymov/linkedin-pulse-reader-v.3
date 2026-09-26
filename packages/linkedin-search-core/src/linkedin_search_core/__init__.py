"""Shared LinkedIn browser session, auth, and errors."""

from .auth.methods import LoginMethod
from .browser.config import BrowserConfig
from .config import LinkedInClientConfig
from .exceptions import (
    BrowserLifecycleError,
    CookieFormatError,
    FeedLoadError,
    LinkedInClientError,
    LoginCancelledError,
    LoginCheckpointError,
    LoginRequiredError,
    LoginTimeoutError,
    PostParseError,
)
from .models.user import UserIdentity
from .session import LinkedInSession

__all__ = [
    "BrowserConfig",
    "BrowserLifecycleError",
    "CookieFormatError",
    "FeedLoadError",
    "LinkedInClientConfig",
    "LinkedInClientError",
    "LinkedInSession",
    "LoginCancelledError",
    "LoginCheckpointError",
    "LoginMethod",
    "LoginRequiredError",
    "LoginTimeoutError",
    "PostParseError",
    "UserIdentity",
]
