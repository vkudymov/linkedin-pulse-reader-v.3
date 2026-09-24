from __future__ import annotations

from typing import Any


def get_user_email(*, client: Any, user_id: str) -> str | None:
    """
    Best-effort: load auth.users email via Supabase admin API (service role).
    """
    try:
        auth = getattr(client, "auth", None)
        admin = getattr(auth, "admin", None) if auth is not None else None
        if admin is None:
            return None
        user_obj = admin.get_user_by_id(user_id)  # type: ignore[attr-defined]
        # supabase-py returns UserResponse(user=User), not a bare user.
        candidate = user_obj
        nested = user_obj.get("user") if isinstance(user_obj, dict) else getattr(user_obj, "user", None)
        if nested is not None:
            candidate = nested
        if isinstance(candidate, dict):
            email = candidate.get("email")
        else:
            email = getattr(candidate, "email", None)
        return email if isinstance(email, str) and email else None
    except Exception:
        return None

