from __future__ import annotations

import sys
from pathlib import Path

# worker/api/src/pulse_api → worker/
_WORKER_ROOT = Path(__file__).resolve().parents[3]
_SESSION_SNAPSHOT_SRC = _WORKER_ROOT / "session_snapshot" / "src"
if _SESSION_SNAPSHOT_SRC.is_dir() and str(_SESSION_SNAPSHOT_SRC) not in sys.path:
    sys.path.insert(0, str(_SESSION_SNAPSHOT_SRC))

__all__ = []

