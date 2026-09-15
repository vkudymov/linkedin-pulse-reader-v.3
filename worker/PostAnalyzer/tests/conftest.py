from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    job_search_src = root.parent / "JobSearch" / "src"
    sys.path.insert(0, str(src))
    if job_search_src.is_dir():
        sys.path.insert(0, str(job_search_src))
