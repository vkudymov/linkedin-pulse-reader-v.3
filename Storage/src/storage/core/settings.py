from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from storage.errors import StorageConfigError


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


_LOCAL_HOSTS: set[str] = {"localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"}


@dataclass(frozen=True, slots=True)
class SupabaseSettings:
    url: str
    key: str
    user_jwt: str | None = None

    @staticmethod
    def from_env(*, user_jwt: str | None = None) -> "SupabaseSettings":
        url = os.getenv("SUPABASE_URL", "").strip()
        key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            or os.getenv("SUPABASE_ANON_KEY", "").strip()
        )

        if not url:
            raise StorageConfigError("SUPABASE_URL is required.")
        if not key:
            raise StorageConfigError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY is required.")

        _validate_cloud_url(url, allow_local=_env_truthy("SUPABASE_ALLOW_LOCAL_URL"))
        return SupabaseSettings(url=url, key=key, user_jwt=user_jwt)


def _validate_cloud_url(url: str, *, allow_local: bool) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").strip().lower()

    if not host:
        raise StorageConfigError("SUPABASE_URL must be a valid URL with hostname.")

    if allow_local:
        return

    if host in _LOCAL_HOSTS:
        raise StorageConfigError(
            "Local SUPABASE_URL is not allowed in cloud-first mode. "
            "Set SUPABASE_ALLOW_LOCAL_URL=1 only for explicit local debugging."
        )

