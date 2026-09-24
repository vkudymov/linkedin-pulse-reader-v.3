from __future__ import annotations

from .export import build_report_file
from .types import EmailMessage, EmailTransport, ReportFormat, ReportItem, ReportMeta, SendResult


def send_search_report(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    file_format: ReportFormat,
    items: list[ReportItem],
    meta: ReportMeta,
    transport: EmailTransport,
) -> SendResult:
    attachment = build_report_file(file_format=file_format, items=items, meta=meta)
    msg = EmailMessage(
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        attachments=([attachment] if attachment is not None else []),
    )
    return transport.send(message=msg)

