from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
_UNSAFE = re.compile(r"[^\w.-]+", re.UNICODE)


def _token(value: str, *, fallback: str) -> str:
    cleaned = _UNSAFE.sub("-", (value or "").strip()).strip("-._")
    return cleaned or fallback


def write_pre_ai_results(
    *,
    user_id: str,
    kind: str,
    search_title: str,
    items: list[dict[str, Any]],
) -> Path:
    """Replace previous `{user}-{kind}*` snapshots, then write the new raw collection."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    user = _token(user_id, fallback="user")
    kind_token = _token(kind, fallback="search")
    search = _token(search_title, fallback="search")
    prefix = f"{user}-{kind_token}"
    for old in RESULTS_DIR.glob(f"{prefix}*"):
        if old.is_file():
            old.unlink()
            log.info("Removed previous result file %s", old.name)
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"{prefix}-{search}-{stamp}.json"
    payload = {
        "user_id": user_id,
        "kind": kind,
        "search_title": search_title,
        "run_at": datetime.now().astimezone().isoformat(),
        "count": len(items),
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Wrote %s (%s items, before AI)", path, len(items))
    return path
