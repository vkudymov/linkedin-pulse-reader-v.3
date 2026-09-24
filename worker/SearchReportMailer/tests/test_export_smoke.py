from __future__ import annotations

from search_report_mailer.export import build_report_file
from search_report_mailer.types import ReportFormat, ReportItem, ReportMeta


def _sample_items() -> list[ReportItem]:
    return [
        ReportItem(
            kind="post",
            analyzed=True,
            match=True,
            score=91,
            reason="Good match",
            matched_requirements=("python", "ai"),
            missing_requirements=(),
            red_flags=(),
            title="Post A",
            url="https://example.com/a",
            text="Hello world",
            comment_text="Nice post",
        ),
        ReportItem(
            kind="post",
            analyzed=True,
            match=False,
            score=40,
            reason="Too junior",
            matched_requirements=(),
            missing_requirements=("senior",),
            red_flags=("low budget",),
            title="Post B",
            url="https://example.com/b",
        ),
        ReportItem(
            kind="post",
            analyzed=False,
            match=None,
            score=None,
            reason="not analyzed",
            title="Post C",
            url="https://example.com/c",
        ),
    ]


def test_build_txt() -> None:
    meta = ReportMeta(kind="post", search_title="Test", run_at_iso="2026-01-01T00:00:00Z", min_score=70)
    a = build_report_file(file_format=ReportFormat.txt, items=_sample_items(), meta=meta)
    assert a is not None
    assert a.filename.endswith(".txt")
    assert b"MATCHED" in a.content


def test_build_json() -> None:
    meta = ReportMeta(kind="post", search_title="Test")
    a = build_report_file(file_format=ReportFormat.json, items=_sample_items(), meta=meta)
    assert a is not None
    assert a.filename.endswith(".json")
    assert b"meta" in a.content and b"items" in a.content


def test_build_xml() -> None:
    meta = ReportMeta(kind="post", search_title="Test")
    a = build_report_file(file_format=ReportFormat.xml, items=_sample_items(), meta=meta)
    assert a is not None
    assert a.filename.endswith(".xml")
    assert a.content.lstrip().startswith(b\"<?xml\")

