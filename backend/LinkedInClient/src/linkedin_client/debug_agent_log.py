from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_DEBUG_LOG_PATH = Path(
    "/Users/vladimirkudymov/Work/linkedin-pulse-reader-v.3/.cursor/debug-5dd403.log"
)


# region agent log
def agent_dbg_log(
    *,
    run_id: str,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
) -> None:
    try:
        payload = {
            "sessionId": "5dd403",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


# endregion
