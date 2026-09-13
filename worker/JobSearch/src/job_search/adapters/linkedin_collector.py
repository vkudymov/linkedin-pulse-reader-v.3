from __future__ import annotations

from dataclasses import dataclass

from job_search.dedupe import compute_source_key
from job_search.domain import Job, JobSearchSpec


def _abs_linkedin_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("/"):
        return f"https://www.linkedin.com{u}"
    return u


@dataclass(frozen=True, slots=True)
class LinkedInJobCollector:
    """
    Adapter: LinkedInClient.fetch_jobs -> JobSearch Job list.

    Notes:
    - Depends on linkedin-client package, but JobSearch core does not.
    """

    client: object

    def collect(self, *, spec: JobSearchSpec) -> list[Job]:
        # Import lazily to keep core portable.
        from linkedin_client import LinkedInClient  # type: ignore[import-untyped]

        if not isinstance(self.client, LinkedInClient):  # pragma: no cover - runtime guard
            raise TypeError("LinkedInJobCollector.client must be a linkedin_client.LinkedInClient")

        raw_jobs = self.client.fetch_jobs(
            keywords=spec.search_query,
            location=spec.location,
            limit=spec.limit,
        )

        out: list[Job] = []
        for j in raw_jobs:
            job_url = _abs_linkedin_url(j.job_url or "")
            title = (j.title or "").strip()
            if not job_url or not title:
                continue

            source_key = compute_source_key(job_url=job_url, linkedin_job_id=j.job_id)
            company_url = _abs_linkedin_url(getattr(j, "company_url", None) or "") or None
            workplace_type = getattr(j, "workplace_type", None) or None
            employment_type = getattr(j, "employment_type", None) or None
            insights = [x for x in (getattr(j, "insights", None) or ()) if isinstance(x, str) and x.strip()]
            out.append(
                Job(
                    source_key=source_key,
                    job_url=job_url,
                    title=title,
                    company=(j.company or None),
                    company_url=company_url,
                    location=(j.location or None),
                    description=(j.description or None),
                    posted_at_text=(j.posted_at_text or None),
                    workplace_type=workplace_type,
                    employment_type=employment_type,
                    raw={
                        "job_id": j.job_id,
                        "job_url": j.job_url,
                        "title": j.title,
                        "company": j.company,
                        "company_url": company_url,
                        "location": j.location,
                        "posted_at_text": j.posted_at_text,
                        "workplace_type": workplace_type,
                        "employment_type": employment_type,
                        "insights": insights,
                    },
                ),
            )

        return out

