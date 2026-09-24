from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from search_report_mailer import send_search_report
from search_report_mailer.types import ReportFormat, ReportItem, ReportMeta, SendResult

from .supabase_functions_transport import build_transport_from_env


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def dispatch_report(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    file_format: ReportFormat,
    items: list[ReportItem],
    meta: ReportMeta,
) -> SendResult:
    transport = build_transport_from_env()
    return send_search_report(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        file_format=file_format,
        items=items,
        meta=meta,
        transport=transport,
    )


def default_subject(*, kind: str, search_title: str) -> str:
    return f"Отчёт поиска ({kind}): {search_title}"


def default_body(*, kind: str, search_title: str) -> str:
    return f"Результаты поиска ({kind}) для: {search_title}"


