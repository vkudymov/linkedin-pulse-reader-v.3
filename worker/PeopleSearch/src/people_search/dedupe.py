from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

_IN_RE = re.compile(r"/in/([^/?#]+)", re.IGNORECASE)


def extract_public_id(profile_url: str) -> str | None:
    m = _IN_RE.search(profile_url or "")
    if not m:
        return None
    pid = m.group(1).strip().rstrip("/")
    return pid or None


def compute_source_key(*, profile_url: str, public_id: str | None = None) -> str:
    pid = (public_id or "").strip() or (extract_public_id(profile_url) or "")
    if pid:
        return f"in:{pid}"
    parsed = urlparse((profile_url or "").strip())
    path = re.sub(r"/+", "/", (parsed.path or "/")).rstrip("/")
    digest = hashlib.sha1(f"{parsed.netloc}{path}".encode("utf-8")).hexdigest()[:12]
    return f"url:{digest}"
