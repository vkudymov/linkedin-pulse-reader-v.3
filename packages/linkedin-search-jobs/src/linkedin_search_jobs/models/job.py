from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Job:
    """
    Minimal LinkedIn Jobs listing model extracted from the UI.

    Best-effort by design: some fields may be None depending on the page variant and account.
    """

    job_id: str | None = None
    job_url: str | None = None
    title: str | None = None
    company: str | None = None
    company_url: str | None = None
    location: str | None = None
    description: str | None = None
    posted_at_text: str | None = None
    workplace_type: str | None = None
    employment_type: str | None = None
    insights: tuple[str, ...] = ()

