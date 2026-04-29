from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
sys.path.insert(0, str(_SRC))


@pytest.fixture(scope="session")
def e2e_enabled() -> bool:
    return os.environ.get("LINKEDIN_E2E", "").lower() in {"1", "true", "yes", "on"}

