"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_core.auth.social import (
    SocialLoginParams,
    SocialLoginFlow,
)

__all__ = ['SocialLoginParams', 'SocialLoginFlow']
