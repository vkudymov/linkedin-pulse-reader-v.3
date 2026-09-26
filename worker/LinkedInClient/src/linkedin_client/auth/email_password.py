"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_core.auth.email_password import (
    EmailPasswordLoginParams,
    EmailPasswordLoginFlow,
)

__all__ = ['EmailPasswordLoginParams', 'EmailPasswordLoginFlow']
