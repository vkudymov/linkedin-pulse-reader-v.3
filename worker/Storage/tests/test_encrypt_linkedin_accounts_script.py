from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.fernet import Fernet

from storage.session_crypto import ENV_NAME, encrypt_json, is_encrypted

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "encrypt_linkedin_accounts.py"


def _load_script() -> Any:
    spec = importlib.util.spec_from_file_location("encrypt_linkedin_accounts", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Query:
    def __init__(self, client: "_Client") -> None:
        self._client = client
        self._mode = "select"
        self._patch: dict[str, Any] | None = None
        self._id: str | None = None

    def select(self, *_a: Any, **_k: Any) -> _Query:
        self._mode = "select"
        return self

    def range(self, *_a: Any, **_k: Any) -> _Query:
        return self

    def update(self, patch: dict[str, Any]) -> _Query:
        self._mode = "update"
        self._patch = patch
        return self

    def eq(self, _col: str, row_id: str) -> _Query:
        self._id = row_id
        return self

    def execute(self) -> SimpleNamespace:
        if self._mode == "select":
            if self._client.selected:
                return SimpleNamespace(data=[])
            self._client.selected = True
            return SimpleNamespace(data=self._client.rows)
        assert self._patch is not None and self._id is not None
        self._client.updates.append((self._id, self._patch))
        return SimpleNamespace(data=[])


class _Client:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.updates: list[tuple[str, dict[str, Any]]] = []
        self.selected = False

    def table(self, name: str) -> _Query:
        assert name == "linkedin_accounts"
        return _Query(self)


def test_script_encrypts_plaintext_and_skips_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_NAME, Fernet.generate_key().decode("ascii"))
    script = _load_script()
    already = encrypt_json([{"name": "li_at", "value": "kept"}])
    client = _Client(
        [
            {
                "id": "plain",
                "cookies_json": [{"name": "li_at", "value": "open-secret", "domain": ".linkedin.com", "path": "/"}],
                "session_snapshot": {"cookies": [{"name": "li_at", "value": "open-secret"}]},
            },
            {
                "id": "done",
                "cookies_json": already,
                "session_snapshot": already,
            },
        ]
    )
    updated, skipped = script.encrypt_existing_accounts(client=client, dry_run=False)
    assert updated == 1
    assert skipped == 1
    row_id, patch = client.updates[0]
    assert row_id == "plain"
    assert is_encrypted(patch["cookies_json"])
    assert is_encrypted(patch["session_snapshot"])
    assert "open-secret" not in patch["cookies_json"]
    assert "open-secret" not in patch["session_snapshot"]
