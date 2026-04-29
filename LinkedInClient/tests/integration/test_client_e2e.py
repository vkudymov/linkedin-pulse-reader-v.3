from __future__ import annotations

import os

import pytest


def _e2e_enabled() -> bool:
    return os.environ.get("LINKEDIN_E2E", "").lower() in {"1", "true", "yes", "on"}


pytestmark = pytest.mark.skipif(not _e2e_enabled(), reason="E2E disabled (set LINKEDIN_E2E=1).")


def test_e2e_placeholder() -> None:
    # Intentionally left as a placeholder: true LinkedIn E2E requires credentials/cookies and
    # is environment-specific. Keep this file as the entrypoint for future E2E expansion.
    assert True

