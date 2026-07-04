from __future__ import annotations

"""
RU: Ошибки библиотеки (публичный контракт).
    Типизированные исключения позволяют внешнему приложению отличать сценарии (auth required,
    lifecycle, feed load) и выбирать стратегию восстановления/ретрая.

EN: Library errors (public contract).
    Typed exceptions let callers distinguish scenarios (auth required, lifecycle, feed load) and
    implement recovery/retry policies safely.
"""


class LinkedInClientError(Exception):
    """Base error for this library."""


class BrowserLifecycleError(LinkedInClientError):
    """Browser/context lifecycle errors (launch, teardown, invalid state)."""


class CookieFormatError(LinkedInClientError):
    """Raised when cookies input is missing required fields or is malformed."""


class LoginRequiredError(LinkedInClientError):
    """Raised when an operation requires an authenticated session."""


class LoginTimeoutError(LinkedInClientError):
    """Raised when manual login did not complete within the configured timeout."""


class LoginCheckpointError(LinkedInClientError):
    """Raised when LinkedIn requires checkpoint / verification to proceed."""


class LoginCancelledError(LinkedInClientError):
    """Raised when the interactive login flow was cancelled by the caller."""


class FeedLoadError(LinkedInClientError):
    """Raised when the LinkedIn feed could not be loaded or stabilized."""


class PostParseError(LinkedInClientError):
    """Raised when post parsing fails unexpectedly."""

