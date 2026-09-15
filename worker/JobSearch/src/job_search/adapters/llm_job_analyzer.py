from __future__ import annotations

import re
from dataclasses import dataclass

from job_search.analysis import JobMatchResult, parse_job_match_json
from job_search.domain import Job, JobSearchSpec

def _extract_json(text: str) -> str:
    """
    Best-effort extraction of a JSON object from LLM output.
    Handles common wrapping like ```json ... ```.
    """
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


def _job_text(job: Job) -> str:
    parts: list[str] = []
    parts.append(f"Title: {job.title}")
    if job.company:
        parts.append(f"Company: {job.company}")
    if job.location:
        parts.append(f"Location: {job.location}")
    if job.workplace_type:
        parts.append(f"Workplace: {job.workplace_type}")
    if job.employment_type:
        parts.append(f"Employment: {job.employment_type}")
    if job.posted_at_text:
        parts.append(f"Posted: {job.posted_at_text}")
    if job.description:
        parts.append("")
        parts.append("Description:")
        parts.append(job.description)
    return "\n".join(parts).strip()


@dataclass(frozen=True, slots=True)
class LlmJobAnalyzer:
    """
    Adapter: LLMClient -> JobMatchResult.

    The core schema is validated by `parse_job_match_json`.
    """

    llm_client: object
    system_prompt: str | None = (
        "You are a strict JSON generator. "
        "Return ONLY valid JSON (no markdown, no commentary)."
    )
    marker: str = "<<<JOB_TEXT>>>"

    def analyze(self, *, spec: JobSearchSpec, job: Job) -> JobMatchResult:
        complete = getattr(self.llm_client, "complete", None)
        if not callable(complete):  # pragma: no cover - runtime guard
            raise TypeError("LlmJobAnalyzer.llm_client must have .complete(system, user) -> str")

        template = (spec.filter_prompt or "").strip()
        if not template:
            raise ValueError("filter_prompt is empty")
        if self.marker not in template:
            raise ValueError(f"filter_prompt must contain marker {self.marker}")

        job_text = _job_text(job)
        user_prompt = template.replace(self.marker, job_text)

        raw = complete(system=self.system_prompt, user=user_prompt)
        extracted = _extract_json(raw)
        return parse_job_match_json(extracted)

