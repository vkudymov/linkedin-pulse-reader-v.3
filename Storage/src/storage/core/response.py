from __future__ import annotations

from typing import Any

from storage.errors import StorageResponseError


def expect_list(resp: Any) -> list[dict[str, Any]]:
    data = getattr(resp, "data", None)
    if not isinstance(data, list):
        raise StorageResponseError(f"Expected list response from Supabase, got: {type(data)}")
    return data


def expect_single(resp: Any) -> dict[str, Any]:
    data = getattr(resp, "data", None)
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    raise StorageResponseError("Expected a single row response from Supabase.")

