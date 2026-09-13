from __future__ import annotations

import re
from dataclasses import dataclass

# LinkedIn insight pills are locale-specific, e.g. "On-site" / "Работа в офисе".

_SPLIT_RE = re.compile(r"\s*[·•|]\s*")
_CRITERIA_RE = re.compile(
    r"(?:employment type|тип занятости|workplace type|формат работы|тип работы)"
    r"\s*[:\n]+\s*([^\n]+)",
    re.IGNORECASE,
)
_NOISE_RE = re.compile(
    r"easy apply|отклик|applicant|соискател|\bago\b|назад|promoted|реклама|"
    r"see more|ещё|alumn|выпускник",
    re.IGNORECASE,
)

_WORKPLACE: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "on_site",
        re.compile(r"on[\s-]?site|in[\s-]?office|работ\w*\s+в\s+офисе|\bв\s+офисе\b", re.I),
    ),
    ("remote", re.compile(r"\bremote\b|work\s+from\s+home|удал[её]нн|дистанцион", re.I)),
    ("hybrid", re.compile(r"\bhybrid\b|гибрид", re.I)),
)

_EMPLOYMENT: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("full_time", re.compile(r"full[\s-]?time|полный\s+рабочий\s+день|полная\s+занятость", re.I)),
    ("part_time", re.compile(r"part[\s-]?time|неполн(?:ый|ая|ую)|частичн", re.I)),
    ("internship", re.compile(r"internship|стажир", re.I)),
    ("freelance", re.compile(r"freelance|фриланс", re.I)),
    ("temporary", re.compile(r"temporary|временн", re.I)),
    ("contract", re.compile(r"\bcontract\b|контракт", re.I)),
)

_KNOWN_KEYS = {key for key, _ in _WORKPLACE} | {key for key, _ in _EMPLOYMENT}


@dataclass(frozen=True, slots=True)
class JobInsights:
    workplace_type: str | None = None
    employment_type: str | None = None
    labels: tuple[str, ...] = ()


def classify_job_insights(
    texts: list[str] | tuple[str, ...] | None = None,
    *,
    location: str | None = None,
    description: str | None = None,
) -> JobInsights:
    workplace: str | None = None
    employment: str | None = None
    labels: list[str] = []
    seen: set[str] = set()

    for raw in _iter_candidates(texts, location=location, description=description):
        if workplace is None:
            key = _match_key(raw, _WORKPLACE)
            if key:
                workplace = key
                _append_label(labels, seen, raw)
                continue
        if employment is None:
            key = _match_key(raw, _EMPLOYMENT)
            if key:
                employment = key
                _append_label(labels, seen, raw)
                continue
        if workplace is not None and employment is not None:
            break

    return JobInsights(
        workplace_type=workplace,
        employment_type=employment,
        labels=tuple(labels),
    )


def normalize_insight_key(value: str | None) -> str | None:
    if not value:
        return None
    t = value.strip()
    if t in _KNOWN_KEYS:
        return t
    return _match_key(t, _WORKPLACE) or _match_key(t, _EMPLOYMENT)


def _iter_candidates(
    texts: list[str] | tuple[str, ...] | None,
    *,
    location: str | None,
    description: str | None,
) -> list[str]:
    out: list[str] = []
    for raw in texts or ():
        out.extend(_split_segments(raw))
    out.extend(_split_segments(location))
    if description:
        for match in _CRITERIA_RE.finditer(description):
            out.extend(_split_segments(match.group(1)))
        out.extend(_split_segments(description[:800]))
        if len(description) > 800:
            out.extend(_split_segments(description[-2000:]))
    return [s for s in out if _usable(s)]


def _split_segments(text: str | None) -> list[str]:
    if not text or not str(text).strip():
        return []
    parts = _SPLIT_RE.split(str(text).strip())
    cleaned: list[str] = []
    for part in parts:
        t = " ".join(part.split())
        if t:
            cleaned.append(t)
    return cleaned


def _usable(text: str) -> bool:
    if len(text) < 3 or len(text) > 64:
        return False
    return not _NOISE_RE.search(text)


def _match_key(text: str, table: tuple[tuple[str, re.Pattern[str]], ...]) -> str | None:
    for key, pattern in table:
        if pattern.search(text):
            return key
    return None


def _append_label(labels: list[str], seen: set[str], raw: str) -> None:
    key = raw.casefold()
    if key in seen:
        return
    seen.add(key)
    labels.append(raw)
