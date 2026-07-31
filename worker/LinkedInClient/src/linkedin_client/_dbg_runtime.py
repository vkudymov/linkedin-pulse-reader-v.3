from __future__ import annotations

import json
import os
import time
from typing import Any


_LOG_PATH = "/Users/vladimirkudymov/Work/LinkedInClient/.cursor/debug-e74afb.log"
_SESSION_ID = "e74afb"


def dbglog(
    *,
    location: str,
    message: str,
    data: dict[str, Any] | None = None,
    hypothesisId: str,
    runId: str,
) -> None:
    """Append one NDJSON line to the debug log (no secrets / no PII)."""
    payload: dict[str, Any] = {
        "sessionId": _SESSION_ID,
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data or {},
        "runId": runId,
        "hypothesisId": hypothesisId,
    }
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        # Never break library flow due to debug logging.
        return

