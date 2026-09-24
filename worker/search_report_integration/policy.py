from __future__ import annotations

from typing import Any

from search_report_mailer.types import ReportFormat


def _as_bool(v: Any) -> bool:
    return bool(v is True or (isinstance(v, str) and v.lower() in ("1", "true", "yes", "on")))


def _as_format(v: Any) -> ReportFormat:
    s = str(v or "").strip().lower()
    try:
        return ReportFormat(s)  # type: ignore[arg-type]
    except Exception:
        return ReportFormat.none


def should_send_email_report(*, tariff_row: dict[str, Any] | None, search_row: dict[str, Any]) -> tuple[bool, ReportFormat]:
    """
    Decide if we should send a report email after a run.

    Returns: (send?, format)
    """
    tariff_allows = _as_bool((tariff_row or {}).get("email_reports_enabled"))
    enabled = _as_bool(search_row.get("email_report_enabled"))
    fmt = _as_format(search_row.get("email_report_format"))

    if not tariff_allows:
        return False, ReportFormat.none
    if not enabled:
        return False, ReportFormat.none
    if fmt == ReportFormat.none:
        return False, ReportFormat.none
    return True, fmt

