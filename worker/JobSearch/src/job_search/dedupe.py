from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

_JOBS_VIEW_RE = re.compile(r"/jobs/view/(\d+)", re.IGNORECASE)


def normalize_job_url(url: str) -> str:
    """
    Make job_url stable for hashing/dedup:
    - drop query/fragment
    - normalize scheme/host/path
    """
    p = urlparse(url.strip())
    scheme = (p.scheme or "https").lower()
    netloc = (p.netloc or "").lower()
    path = re.sub(r"/+", "/", (p.path or "/")).rstrip("/")
    if not path:
        path = "/"
    return f"{scheme}://{netloc}{path}"


def extract_linkedin_job_id(job_url: str) -> str | None:
    m = _JOBS_VIEW_RE.search(job_url)
    return m.group(1) if m else None


def compute_source_key(*, job_url: str, linkedin_job_id: str | None = None) -> str:
    """
    Stable key used for dedup/upsert.
    """
    jid = (linkedin_job_id or "").strip()
    if jid:
        return f"job:{jid}"

    if (from_url := extract_linkedin_job_id(job_url or "")) is not None:
        return f"job:{from_url}"

    u = normalize_job_url(job_url or "")
    if u.startswith("http"):
        digest = hashlib.sha1(u.encode("utf-8")).hexdigest()[:12]
        return f"url:{digest}"

    digest = hashlib.sha1((job_url or "").encode("utf-8")).hexdigest()[:12]
    return f"fallback:{digest}"


def dedupe_by_source_key(items: list[tuple[str, object]]) -> list[tuple[str, object]]:
    seen: set[str] = set()
    out: list[tuple[str, object]] = []
    for key, item in items:
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((key, item))
    return out

