"""Compatibility re-export. Implementation lives in the linkedin-search packages."""

from linkedin_search_core.auth.wait import (
    SessionWaitConfig,
    wait_for_session,
)

__all__ = ['SessionWaitConfig', 'wait_for_session']
