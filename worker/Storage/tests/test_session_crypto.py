from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.fernet import Fernet

from storage.domain.pulse.linkedin_accounts import LinkedInAccountRepository
from storage.session_crypto import (
    ENV_NAME,
    SessionCryptoError,
    decrypt_json,
    encrypt_json,
    is_encrypted,
)


@pytest.fixture
def fernet_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv(ENV_NAME, key)
    return key


def test_roundtrip_preserves_playwright_cookie_list(fernet_key: str) -> None:
    cookies = [
        {"name": "li_at", "value": "session-secret", "domain": ".linkedin.com", "path": "/", "secure": True}
    ]
    token = encrypt_json(cookies)
    assert is_encrypted(token)
    assert "session-secret" not in token
    assert decrypt_json(token) == cookies


def test_legacy_plaintext_passes_through_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)
    cookies = [{"name": "li_at", "value": "plain", "domain": ".linkedin.com", "path": "/"}]
    assert decrypt_json(cookies) == cookies
    assert decrypt_json(None) is None


def test_missing_key_does_not_echo_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)
    secret = "li_at-value-should-not-leak"
    with pytest.raises(SessionCryptoError) as exc:
        encrypt_json([{"value": secret}])
    assert secret not in str(exc.value)
    assert exc.value.__cause__ is None


def test_bad_token_does_not_echo_ciphertext(fernet_key: str) -> None:
    with pytest.raises(SessionCryptoError) as exc:
        decrypt_json("enc:v1:not-a-token")
    assert "not-a-token" not in str(exc.value)


class _Query:
    def __init__(self, client: "_Client", payload: dict[str, Any] | None = None) -> None:
        self._client = client
        self._payload = payload

    def select(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def eq(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def order(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def insert(self, payload: dict[str, Any]) -> _Query:
        self._client.writes.append(payload)
        return _Query(self._client, payload)

    def update(self, payload: dict[str, Any]) -> _Query:
        self._client.writes.append(payload)
        return _Query(self._client, payload)

    def execute(self) -> SimpleNamespace:
        if self._payload is None:
            return SimpleNamespace(data=self._client.rows)
        row = {"id": "acc-1", "user_id": "user-1", **self._payload}
        return SimpleNamespace(data=[row])


class _Client:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.writes: list[dict[str, Any]] = []

    def table(self, name: str) -> _Query:
        assert name == "linkedin_accounts"
        return _Query(self)


def test_repository_seals_on_write_and_opens_on_read(fernet_key: str) -> None:
    snapshot = {
        "cookies": [
            {"name": "li_at", "value": "session-secret", "domain": ".linkedin.com", "path": "/"}
        ]
    }
    client = _Client()
    repo = LinkedInAccountRepository(client)
    created = repo.create(user_id="user-1", session_snapshot=snapshot)

    stored = client.writes[0]
    assert is_encrypted(stored["cookies_json"])
    assert is_encrypted(stored["session_snapshot"])
    assert "session-secret" not in stored["cookies_json"]
    assert "session-secret" not in stored["session_snapshot"]
    assert created["session_snapshot"]["cookies"][0]["value"] == "session-secret"
    assert isinstance(created["cookies_json"], list)
    assert created["cookies_json"][0]["name"] == "li_at"

    client.rows = [
        {
            "id": "acc-1",
            "user_id": "user-1",
            "label": None,
            "cookies_json": stored["cookies_json"],
            "session_snapshot": stored["session_snapshot"],
        }
    ]
    loaded = repo.list_by_user(user_id="user-1")
    assert loaded[0]["session_snapshot"]["cookies"][0]["value"] == "session-secret"
    assert loaded[0]["cookies_json"][0]["value"] == "session-secret"
