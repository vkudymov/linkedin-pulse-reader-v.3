from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Header, HTTPException, status

from ..settings import get_settings


@lru_cache(maxsize=1)
def _get_supabase_admin_client() -> Any:
    settings = get_settings()
    from supabase import create_client  # type: ignore[import-untyped]

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_access_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header.")
    return parts[1].strip()

def require_user_id(authorization: str | None = Header(default=None)) -> str:
    token = get_access_token(authorization)
    client = _get_supabase_admin_client()
    try:
        resp = client.auth.get_user(token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from e

    user: Any = getattr(resp, "user", None)
    if user is None and isinstance(resp, dict):
        user = resp.get("user")
    user_id = getattr(user, "id", None) if user is not None else None
    if user_id is None and isinstance(user, dict):
        user_id = user.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return user_id

