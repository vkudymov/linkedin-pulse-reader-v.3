from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """
    Minimal representation of a LinkedIn identity.

    This library is intentionally light on user management; the calling application owns
    credential storage and account/user lifecycle.
    """

    profile_url: str | None = None
    urn: str | None = None

