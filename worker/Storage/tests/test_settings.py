from __future__ import annotations

import os

import pytest

from storage.errors import StorageConfigError
from storage import SupabaseSettings


def test_from_env_rejects_localhost_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.delenv("SUPABASE_ALLOW_LOCAL_URL", raising=False)

    with pytest.raises(StorageConfigError):
        SupabaseSettings.from_env()


def test_from_env_allows_localhost_with_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:54321")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_ALLOW_LOCAL_URL", "1")

    s = SupabaseSettings.from_env()
    assert s.url.startswith("http://127.0.0.1:")


def test_from_env_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_ALLOW_LOCAL_URL", "1")

    with pytest.raises(StorageConfigError):
        SupabaseSettings.from_env()


def test_from_env_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    with pytest.raises(StorageConfigError):
        SupabaseSettings.from_env()

