from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from linkedin_search_people.navigation.boolean_query import normalize_boolean_query

NETWORK_CODES = {"F", "S", "O"}
# LinkedIn industry facet ids. Names are labels for the UI; numeric ids go into `industry`.
PEOPLE_INDUSTRIES: tuple[tuple[str, str], ...] = (
    ("4", "Software Development"),
    ("6", "Technology, Information and Internet"),
    ("96", "IT Services and IT Consulting"),
    ("3", "Computer Hardware"),
    ("8", "Computer Networking Products"),
    ("7", "Semiconductor Manufacturing"),
    ("24", "Telecommunications"),
    ("118", "Research Services"),
    ("11", "Business Consulting and Services"),
    ("43", "Financial Services"),
    ("41", "Banking"),
    ("80", "Advertising Services"),
    ("137", "Human Resources Services"),
    ("14", "Higher Education"),
    ("25", "Manufacturing"),
    ("15", "Pharmaceutical Manufacturing"),
    ("186", "Information Services"),
    ("109", "Computer Games"),
)
PEOPLE_INDUSTRY_IDS = {iid for iid, _ in PEOPLE_INDUSTRIES}
PROFILE_LANGUAGES = {
    "en",
    "ru",
    "de",
    "fr",
    "es",
    "it",
    "pt",
    "nl",
    "pl",
    "tr",
    "zh",
    "ja",
    "ko",
    "ar",
}

DEFAULT_PEOPLE_FILTERS: dict[str, Any] = {
    "network": [],
    "locations": [],
    "current_company": [],
    "past_company": [],
    "school": [],
    "industry": [],
    "profile_language": "",
    "keywords": "",
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, (int, float)) and not isinstance(item, bool):
                out.append(str(int(item)))
        return out
    return []


def resolve_people_filters(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_PEOPLE_FILTERS)
    if not isinstance(raw, Mapping) or not raw:
        return out
    for key in DEFAULT_PEOPLE_FILTERS:
        if key not in raw or raw[key] is None:
            continue
        if key == "profile_language":
            lang = str(raw[key]).strip().lower()
            out[key] = lang if lang in PROFILE_LANGUAGES else ""
        elif key == "keywords":
            out[key] = str(raw[key]).strip()
        elif key == "network":
            codes = [c.upper() for c in _as_list(raw[key])]
            out[key] = [c for c in codes if c in NETWORK_CODES]
        else:
            out[key] = _as_list(raw[key])
    return out


def compose_people_keywords(base: str, filters: Mapping[str, Any] | None) -> str:
    resolved = resolve_people_filters(filters)
    keywords = (base or "").strip()
    extra = str(resolved.get("keywords") or "").strip()
    if extra:
        lowered = keywords.casefold()
        if extra.casefold() not in lowered:
            keywords = f"{keywords} {extra}".strip()
    normalized = normalize_boolean_query(keywords)
    return normalized.query


def _facet_ids(values: Sequence[str]) -> list[str]:
    ids: list[str] = []
    for v in values:
        if v.isdigit():
            ids.append(v)
            continue
        if ":" in v and v.split(":")[-1].isdigit():
            ids.append(v.split(":")[-1])
    return ids


def _non_numeric(values: Sequence[str]) -> list[str]:
    return [v for v in values if v and not v.isdigit() and not (":" in v and v.split(":")[-1].isdigit())]


def _json_list(values: Sequence[str]) -> str:
    return json.dumps(list(values), separators=(",", ":"))


def build_people_search_query(
    *,
    keywords: str,
    filters: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    resolved = resolve_people_filters(filters)
    composed = compose_people_keywords(keywords, resolved)
    extras: list[str] = []
    extras.extend(_non_numeric(resolved["locations"]))
    extras.extend(_non_numeric(resolved["current_company"]))
    extras.extend(_non_numeric(resolved["past_company"]))
    extras.extend(_non_numeric(resolved["school"]))
    extras.extend(_non_numeric(resolved["industry"]))
    lowered = composed.casefold()
    for extra in extras:
        quoted = extra if extra.startswith('"') else f'"{extra}"'
        if extra.casefold() not in lowered and quoted.casefold() not in lowered:
            composed = f"{composed} {quoted}".strip()
            lowered = composed.casefold()

    q: dict[str, str] = {"origin": "FACETED_SEARCH"}
    if composed:
        q["keywords"] = composed

    network = resolved["network"]
    if network:
        q["network"] = _json_list(network)

    geo_ids = _facet_ids(resolved["locations"])
    if geo_ids:
        q["geoUrn"] = _json_list(geo_ids)

    current = _facet_ids(resolved["current_company"])
    if current:
        q["currentCompany"] = _json_list(current)

    past = _facet_ids(resolved["past_company"])
    if past:
        q["pastCompany"] = _json_list(past)

    school = _facet_ids(resolved["school"])
    if school:
        q["schoolFilter"] = _json_list(school)

    industry = _facet_ids(resolved["industry"])
    if industry:
        q["industry"] = _json_list(industry)

    lang = str(resolved.get("profile_language") or "").strip()
    if lang:
        q["profileLanguage"] = _json_list([lang])

    return q


def build_people_search_url(
    *,
    base_url: str = "https://www.linkedin.com/search/results/people/",
    keywords: str,
    filters: Mapping[str, Any] | None = None,
) -> str:
    q = build_people_search_query(keywords=keywords, filters=filters)
    return f"{base_url}?{urlencode(q)}"
