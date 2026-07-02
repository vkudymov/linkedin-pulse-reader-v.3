from __future__ import annotations

from typing import Any

from .core.client import create_supabase_client
from .domain.pulse import FeedPostRepository, LinkedInAccountRepository


class PulseStorage:
    """
    Facade for the current LinkedIn Pulse storage domain.

    Expects SUPABASE_SERVICE_ROLE_KEY in worker/demo runs (RLS bypass for ingestion).
    """

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or create_supabase_client()
        self.linkedin_accounts = LinkedInAccountRepository(self.client)
        self.feed_posts = FeedPostRepository(self.client)

