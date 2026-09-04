from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .linkedin import DEFAULT_ORIGIN


def apply_storage_snapshot(page: Any, storage_snapshot: dict[str, Any]) -> None:
    local_items = storage_snapshot.get("localStorage", {})
    session_items = storage_snapshot.get("sessionStorage", {})
    page.evaluate(
        """({ localItems, sessionItems }) => {
            localStorage.clear();
            sessionStorage.clear();
            for (const [k, v] of Object.entries(localItems || {})) {
                localStorage.setItem(k, v ?? "");
            }
            for (const [k, v] of Object.entries(sessionItems || {})) {
                sessionStorage.setItem(k, v ?? "");
            }
        }""",
        {"localItems": local_items, "sessionItems": session_items},
    )


def capture_storage_from_page(page: Any) -> dict[str, Any]:
    snapshot = page.evaluate(
        """() => ({
            origin: window.location.origin,
            localStorage: Object.fromEntries(
                Object.keys(localStorage).map((key) => [key, localStorage.getItem(key)])
            ),
            sessionStorage: Object.fromEntries(
                Object.keys(sessionStorage).map((key) => [key, sessionStorage.getItem(key)])
            ),
        })"""
    )
    if not isinstance(snapshot, dict):
        return {"origin": "", "localStorage": {}, "sessionStorage": {}}
    return {
        "origin": snapshot.get("origin") or "",
        "localStorage": snapshot.get("localStorage") or {},
        "sessionStorage": snapshot.get("sessionStorage") or {},
    }


def _storage_has_keys(storage: dict[str, Any]) -> bool:
    local_items = storage.get("localStorage") or {}
    session_items = storage.get("sessionStorage") or {}
    return bool(local_items) or bool(session_items)


def _origin_is_valid(origin: str) -> bool:
    parsed = urlparse(origin.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def seed_origin_storage(page: Any, storage: dict[str, Any]) -> None:
    if not isinstance(storage, dict):
        return
    origin = str(storage.get("origin") or DEFAULT_ORIGIN).strip()
    if not _origin_is_valid(origin):
        return
    if not _storage_has_keys(storage):
        return
    page.goto(origin, wait_until="commit")
    apply_storage_snapshot(page, storage)
