from __future__ import annotations

import json
import os
from typing import Any

from storage.errors import StorageError

ENV_NAME = "LINKEDIN_COOKIES_ENCRYPTION_KEY"
PREFIX = "enc:v1:"


class SessionCryptoError(StorageError):
    """Encryption key or payload problem. Message never includes session plaintext."""


def is_encrypted(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt_json(value: Any) -> str:
    """Serialize ``value`` and return an ``enc:v1:`` Fernet token."""
    try:
        payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except TypeError:
        raise SessionCryptoError("LinkedIn session field is not JSON-serializable.") from None
    token = _fernet().encrypt(payload).decode("ascii")
    return PREFIX + token


def decrypt_json(value: Any) -> Any:
    """
    Return plaintext JSON.

    Legacy rows (list/dict, or any value without the prefix) pass through so
    Playwright still receives the original cookie list or snapshot dict.
    """
    if not is_encrypted(value):
        return value
    token = str(value)[len(PREFIX) :].encode("ascii")
    try:
        plain = _fernet().decrypt(token)
    except Exception:
        raise SessionCryptoError("Failed to decrypt LinkedIn session field.") from None
    try:
        return json.loads(plain.decode("utf-8"))
    except Exception:
        raise SessionCryptoError("Decrypted LinkedIn session field is not valid JSON.") from None


def _fernet() -> Any:
    raw = os.environ.get(ENV_NAME, "").strip()
    if not raw:
        raise SessionCryptoError(f"{ENV_NAME} is not set.")
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise SessionCryptoError("cryptography is required to encrypt LinkedIn sessions.") from None
    try:
        return Fernet(raw.encode("utf-8"))
    except Exception:
        raise SessionCryptoError(f"{ENV_NAME} is not a valid Fernet key.") from None
