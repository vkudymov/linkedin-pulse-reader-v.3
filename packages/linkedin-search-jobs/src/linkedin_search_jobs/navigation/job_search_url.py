from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

DEFAULT_JOB_FILTERS: dict[str, Any] = {
    "date_posted": "week",
    "remote": False,
    "easy_apply": False,
    "experience": "any",
    "employment": "full_time",
    "company": "",
}

_DATE_POSTED = {
    "day": "r86400",
    "week": "r604800",
    "month": "r2592000",
}
_EXPERIENCE = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid_senior": "4",
    "director": "5",
    "executive": "6",
}
_EMPLOYMENT = {
    "full_time": "F",
    "part_time": "P",
    "contract": "C",
    "temporary": "T",
    "internship": "I",
}


def resolve_job_filters(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_JOB_FILTERS)
    if not isinstance(raw, Mapping) or not raw:
        return out
    for key in DEFAULT_JOB_FILTERS:
        if key in raw and raw[key] is not None:
            out[key] = raw[key]
    if not isinstance(out["company"], str):
        out["company"] = ""
    else:
        out["company"] = out["company"].strip()
    out["remote"] = bool(out["remote"])
    out["easy_apply"] = bool(out["easy_apply"])
    return out


def compose_job_keywords(base: str, filters: Mapping[str, Any] | None) -> str:
    resolved = resolve_job_filters(filters)
    keywords = (base or "").strip()
    extras: list[str] = []
    company = resolved["company"]
    if company and not company.isdigit():
        extras.append(company)
    lowered = keywords.casefold()
    for extra in extras:
        if extra.casefold() not in lowered:
            keywords = f"{keywords} {extra}".strip()
            lowered = keywords.casefold()
    return keywords


def build_jobs_search_query(
    *,
    keywords: str,
    location: str | None,
    filters: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    resolved = resolve_job_filters(filters)
    composed = compose_job_keywords(keywords, resolved)
    q: dict[str, str] = {"keywords": composed}
    if location and str(location).strip():
        q["location"] = str(location).strip()

    date_key = str(resolved.get("date_posted") or "")
    if date_key in _DATE_POSTED:
        q["f_TPR"] = _DATE_POSTED[date_key]
    if resolved.get("remote"):
        q["f_WT"] = "2"
    if resolved.get("easy_apply"):
        q["f_AL"] = "true"
    exp_key = str(resolved.get("experience") or "")
    if exp_key in _EXPERIENCE:
        q["f_E"] = _EXPERIENCE[exp_key]
    emp_key = str(resolved.get("employment") or "")
    if emp_key in _EMPLOYMENT:
        q["f_JT"] = _EMPLOYMENT[emp_key]
    company = str(resolved.get("company") or "").strip()
    if company.isdigit():
        q["f_C"] = company
    return q


def build_jobs_search_url(
    *,
    base_url: str,
    keywords: str,
    location: str | None,
    filters: Mapping[str, Any] | None = None,
) -> str:
    q = build_jobs_search_query(keywords=keywords, location=location, filters=filters)
    return f"{base_url}?{urlencode(q)}"
