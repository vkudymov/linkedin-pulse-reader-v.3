from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class SnapshotStorage(TypedDict, total=False):
    origin: str
    localStorage: dict[str, Any]
    sessionStorage: dict[str, Any]


class SnapshotDiagnostics(TypedDict, total=False):
    cookieCount: int
    captured_at: str
    source: str


class SessionSnapshot(TypedDict, total=False):
    createdAt: NotRequired[str]
    cookies: list[dict[str, Any]]
    storage: NotRequired[SnapshotStorage]
    browser: NotRequired[dict[str, Any]]
    viewport: NotRequired[dict[str, Any]]
    tab: NotRequired[dict[str, Any]]
    diagnostics: NotRequired[SnapshotDiagnostics]
