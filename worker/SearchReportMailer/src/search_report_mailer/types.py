from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Literal, Protocol, Sequence


ReportKind = Literal["post", "job"]


class ReportFormat(str, Enum):
    none = "none"
    xlsx = "xlsx"
    docx = "docx"
    txt = "txt"
    json = "json"
    xml = "xml"


@dataclass(frozen=True, slots=True)
class ReportMeta:
    kind: ReportKind
    search_title: str
    run_at_iso: str | None = None
    min_score: int | None = None
    target_found: int | None = None
    fetched_count: int | None = None
    analyzed_count: int | None = None
    matched_count: int | None = None


@dataclass(frozen=True, slots=True)
class ReportItem:
    """
    A portable, storage-agnostic snapshot of one analyzed entity (post/job).

    match/score/reason/requirements fields come from the analyzer (when available).
    If an item was not analyzed (e.g. early-stop when target found), set:
      analyzed=False, match=None, score=None, reason="not analyzed"
    """

    kind: ReportKind
    analyzed: bool
    match: bool | None
    score: int | None
    reason: str | None
    matched_requirements: Sequence[str] = ()
    missing_requirements: Sequence[str] = ()
    red_flags: Sequence[str] = ()

    title: str | None = None
    url: str | None = None
    text: str | None = None  # post content or job summary (optional)

    company: str | None = None
    location: str | None = None
    description: str | None = None

    comment_text: str | None = None
    extra: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EmailAttachment:
    filename: str
    mime_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to_email: str
    subject: str
    body_text: str
    attachments: Sequence[EmailAttachment] = ()


@dataclass(frozen=True, slots=True)
class SendResult:
    ok: bool
    provider: str | None = None
    message_id: str | None = None
    error: str | None = None
    raw: Any | None = None


class EmailTransport(Protocol):
    def send(self, *, message: EmailMessage) -> SendResult: ...


def as_lines(v: str | Iterable[str] | None) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [line for line in v.splitlines() if line.strip()]
    return [str(x) for x in v if str(x).strip()]

