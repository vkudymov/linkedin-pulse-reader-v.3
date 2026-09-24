from __future__ import annotations

from datetime import datetime

from .formats.docx import build_docx
from .formats.json_format import build_json
from .formats.txt import build_txt
from .formats.xlsx import build_xlsx
from .formats.xml_format import build_xml
from .types import EmailAttachment, ReportFormat, ReportItem, ReportMeta


def _default_filename(meta: ReportMeta, fmt: ReportFormat) -> str:
    safe_title = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (meta.search_title or "search"))
    ts = (meta.run_at_iso or datetime.utcnow().isoformat()).replace(":", "-")
    return f"{meta.kind}_{safe_title}_{ts}.{fmt.value}"


def build_report_file(*, file_format: ReportFormat, items: list[ReportItem], meta: ReportMeta) -> EmailAttachment | None:
    if file_format == ReportFormat.none:
        return None

    if file_format == ReportFormat.txt:
        content = build_txt(items=items, meta=meta)
        return EmailAttachment(filename=_default_filename(meta, file_format), mime_type="text/plain; charset=utf-8", content=content)

    if file_format == ReportFormat.json:
        content = build_json(items=items, meta=meta)
        return EmailAttachment(filename=_default_filename(meta, file_format), mime_type="application/json; charset=utf-8", content=content)

    if file_format == ReportFormat.xml:
        content = build_xml(items=items, meta=meta)
        return EmailAttachment(filename=_default_filename(meta, file_format), mime_type="application/xml; charset=utf-8", content=content)

    if file_format == ReportFormat.xlsx:
        content = build_xlsx(items=items, meta=meta)
        return EmailAttachment(filename=_default_filename(meta, file_format), mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", content=content)

    if file_format == ReportFormat.docx:
        content = build_docx(items=items, meta=meta)
        return EmailAttachment(filename=_default_filename(meta, file_format), mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", content=content)

    raise ValueError(f"Unsupported report format: {file_format}")

