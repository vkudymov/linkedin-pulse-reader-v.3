from __future__ import annotations

import re
from dataclasses import dataclass

from people_search.analysis import PeopleMatchResult, parse_people_match_json
from people_search.domain import PeopleSearchSpec, PersonProfile

DEFAULT_MATCH_SYSTEM_PROMPT = (
    "You are a strict JSON generator. "
    "Return ONLY valid JSON (no markdown, no commentary)."
)


def extract_llm_json(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return t
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*```$", "", t)
    if t.startswith("{") and t.endswith("}"):
        return t
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        return t[start : end + 1]
    return t


def analyze_template(
    *,
    llm_client: object,
    template: str,
    marker: str,
    body_text: str,
    system_prompt: str | None = DEFAULT_MATCH_SYSTEM_PROMPT,
) -> PeopleMatchResult:
    complete = getattr(llm_client, "complete", None)
    if not callable(complete):  # pragma: no cover
        raise TypeError("llm_client must have .complete(system, user) -> str")

    tmpl = (template or "").strip()
    if not tmpl:
        raise ValueError("prompt is empty")
    if marker not in tmpl:
        raise ValueError(f"prompt must contain marker {marker}")

    user_prompt = tmpl.replace(marker, body_text)
    raw = complete(system=system_prompt, user=user_prompt)
    return parse_people_match_json(extract_llm_json(raw))


def _profile_text(person: PersonProfile) -> str:
    parts: list[str] = []
    if person.full_name:
        parts.append(f"Name: {person.full_name}")
    if person.headline:
        parts.append(f"Headline: {person.headline}")
    if person.location:
        parts.append(f"Location: {person.location}")
    if person.connection_degree:
        parts.append(f"Connection: {person.connection_degree}")
    if person.current_company:
        parts.append(f"Current company: {person.current_company}")
    if person.skills:
        parts.append("Skills: " + ", ".join(person.skills))
    if person.snippet:
        parts.append("")
        parts.append("Snippet:")
        parts.append(person.snippet)
    if person.about:
        parts.append("")
        parts.append("About:")
        parts.append(person.about)
    if person.experience:
        parts.append("")
        parts.append("Experience:")
        for item in person.experience:
            title = item.get("title") if isinstance(item, dict) else None
            text = item.get("text") if isinstance(item, dict) else None
            parts.append(f"- {title or text or item}")
    if person.education:
        parts.append("")
        parts.append("Education:")
        for item in person.education:
            title = item.get("title") if isinstance(item, dict) else None
            text = item.get("text") if isinstance(item, dict) else None
            parts.append(f"- {title or text or item}")
    if person.profile_url:
        parts.append("")
        parts.append(f"Profile URL: {person.profile_url}")
    return "\n".join(parts).strip()


@dataclass(frozen=True, slots=True)
class LlmPeopleAnalyzer:
    llm_client: object
    system_prompt: str | None = DEFAULT_MATCH_SYSTEM_PROMPT
    marker: str = "<<<PROFILE_TEXT>>>"

    def analyze(self, *, spec: PeopleSearchSpec, person: PersonProfile) -> PeopleMatchResult:
        return analyze_template(
            llm_client=self.llm_client,
            template=spec.prompt or "",
            marker=self.marker,
            body_text=_profile_text(person),
            system_prompt=self.system_prompt,
        )
