from __future__ import annotations

import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_CLIENT_ERROR_LIMIT = 240


def extract_error_line(output: str) -> str | None:
    cleaned = _ANSI_RE.sub("", output or "")
    for line in cleaned.splitlines():
        candidate = line.strip()
        if candidate.startswith("ERROR:"):
            return candidate
    return None


def client_failure_message(output: str, *, fallback: str) -> str:
    """Short text for API clients. Raw worker stdout stays in server logs."""
    line = extract_error_line(output)
    if line:
        return line[:_CLIENT_ERROR_LIMIT]
    return fallback


def short_stored_error(error: str | None, *, fallback: str) -> str:
    if not error or not error.strip():
        return fallback
    line = error.strip().splitlines()[0].strip()
    if not line or len(line) > _CLIENT_ERROR_LIMIT:
        return fallback
    if len(error) > _CLIENT_ERROR_LIMIT and not line.startswith("ERROR:"):
        return fallback
    return line
