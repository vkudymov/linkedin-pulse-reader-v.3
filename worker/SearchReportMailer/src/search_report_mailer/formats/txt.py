from __future__ import annotations

from ..types import ReportItem, ReportMeta, as_lines


def _fmt_reqs(label: str, xs: list[str]) -> str:
    if not xs:
        return ""
    return f"{label}: " + "; ".join(xs) + "\n"


def build_txt(*, items: list[ReportItem], meta: ReportMeta) -> bytes:
    matched = [i for i in items if i.analyzed and i.match is True]
    not_matched = [i for i in items if i.analyzed and i.match is False]
    not_analyzed = [i for i in items if not i.analyzed]

    lines: list[str] = []
    lines.append(f"Search report ({meta.kind})")
    lines.append(f"Title: {meta.search_title}")
    if meta.run_at_iso:
        lines.append(f"Run at: {meta.run_at_iso}")
    if meta.min_score is not None:
        lines.append(f"Min score: {meta.min_score}")
    if meta.target_found is not None:
        lines.append(f"Target found: {meta.target_found}")
    if meta.fetched_count is not None:
        lines.append(f"Fetched: {meta.fetched_count}")
    if meta.analyzed_count is not None:
        lines.append(f"Analyzed: {meta.analyzed_count}")
    if meta.matched_count is not None:
        lines.append(f"Matched: {meta.matched_count}")
    lines.append("")

    def render_section(title: str, section_items: list[ReportItem]) -> None:
        lines.append(title)
        lines.append("=" * len(title))
        if not section_items:
            lines.append("(empty)")
            lines.append("")
            return
        for idx, i in enumerate(section_items, start=1):
            lines.append(f"{idx}. {i.title or '<no title>'}")
            if i.url:
                lines.append(f"   URL: {i.url}")
            if i.company:
                lines.append(f"   Company: {i.company}")
            if i.location:
                lines.append(f"   Location: {i.location}")
            if i.score is not None:
                lines.append(f"   Score: {i.score}")
            if i.reason:
                lines.append(f"   Reason: {i.reason}")
            m = as_lines(i.matched_requirements)
            mm = as_lines(i.missing_requirements)
            rf = as_lines(i.red_flags)
            reqs = ""
            reqs += _fmt_reqs("Matched", m)
            reqs += _fmt_reqs("Missing", mm)
            reqs += _fmt_reqs("Red flags", rf)
            if reqs:
                for ln in reqs.rstrip("\n").splitlines():
                    lines.append("   " + ln)
            if i.comment_text:
                lines.append("   Comment:")
                for ln in (i.comment_text or "").splitlines():
                    lines.append("     " + ln)
            if i.text:
                lines.append("   Text:")
                for ln in (i.text or "").splitlines()[:50]:
                    lines.append("     " + ln)
                if len((i.text or "").splitlines()) > 50:
                    lines.append("     ...")
            if i.description and not i.text:
                lines.append("   Description:")
                for ln in (i.description or "").splitlines()[:50]:
                    lines.append("     " + ln)
                if len((i.description or "").splitlines()) > 50:
                    lines.append("     ...")
            lines.append("")

    render_section("MATCHED", matched)
    render_section("NOT_MATCHED", not_matched)
    render_section("NOT_ANALYZED", not_analyzed)

    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")

