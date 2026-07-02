from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .settings import SupabaseSettings

if TYPE_CHECKING:  # pragma: no cover
    from supabase import Client  # type: ignore[import-untyped]


def create_supabase_client(
    *,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
    user_jwt: str | None = None,
) -> "Client":
    """
    Create a Supabase client.

    - `SUPABASE_SERVICE_ROLE_KEY` is for backend/worker access and bypasses RLS.
    - `SUPABASE_ANON_KEY` + `user_jwt` is for user-facing access where RLS applies.
    """

    settings = (
        SupabaseSettings(url=supabase_url, key=supabase_key, user_jwt=user_jwt)  # type: ignore[arg-type]
        if (supabase_url is not None and supabase_key is not None)
        else SupabaseSettings.from_env(user_jwt=user_jwt)
    )

    from supabase import create_client  # type: ignore[import-untyped]

    client_options = _make_client_options(user_jwt=settings.user_jwt)
    if client_options is not None:
        return create_client(settings.url, settings.key, options=client_options)

    client = create_client(settings.url, settings.key)
    if settings.user_jwt:
        _try_attach_jwt(client, settings.user_jwt)
    return client


def _make_client_options(*, user_jwt: str | None) -> Any | None:
    if not user_jwt:
        return None

    try:
        from supabase.lib.client_options import ClientOptions  # type: ignore[import-untyped]
    except Exception:  # pragma: no cover - best-effort compatibility
        return None

    return ClientOptions(headers={"Authorization": f"Bearer {user_jwt}"})


def _try_attach_jwt(client: Any, user_jwt: str) -> None:
    for attr in ("postgrest", "rest"):
        obj: Any = getattr(client, attr, None)
        if obj is None:
            continue
        try:
            auth_fn = getattr(obj, "auth", None)
            if callable(auth_fn):
                auth_fn(user_jwt)
        except Exception:
            continue

