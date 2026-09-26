from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from time import monotonic
from urllib.parse import urlparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from ..exceptions import LoginCancelledError, LoginCheckpointError, LoginTimeoutError


@dataclass(frozen=True, slots=True)
class SessionWaitConfig:
    timeout_ms: int
    cancelled: Callable[[], bool] | None = None
    on_checkpoint: Callable[[], None] | None = None
    raise_on_checkpoint: bool = False


def wait_for_session(page: Page, *, cfg: SessionWaitConfig) -> None:
    """
    Wait until LinkedIn session becomes authenticated (feed redirect/layout).

    This is intentionally best-effort and UI-driven:
    - If LinkedIn redirects to /feed, cookies are usable.
    - If LinkedIn shows checkpoint/challenge, the user must complete it.
    """
    deadline = monotonic() + max(cfg.timeout_ms, 0) / 1000.0
    checkpoint_notified = False

    while monotonic() < deadline:
        if cfg.cancelled is not None and cfg.cancelled():
            raise LoginCancelledError("Login flow cancelled by caller.")

        url = _safe_url(page)
        if _is_logged_in_url(url):
            return

        if _is_linkedin_url(url) and (_is_checkpoint_url(url) or _looks_like_checkpoint_page(page)):
            if cfg.raise_on_checkpoint and cfg.on_checkpoint is None:
                raise LoginCheckpointError(
                    "LinkedIn requires verification (checkpoint). "
                    "Complete it in the opened browser window."
                )
            if not checkpoint_notified:
                checkpoint_notified = True
                if cfg.on_checkpoint is not None:
                    with suppress(Exception):
                        cfg.on_checkpoint()

        remaining_ms = int(max(0.0, (deadline - monotonic()) * 1000.0))
        slice_ms = min(1500, remaining_ms) if remaining_ms else 0

        # Prefer URL-based signal, but don't block for the entire timeout in one call.
        if slice_ms:
            with suppress(PlaywrightTimeoutError):
                page.wait_for_url("**/feed/**", timeout=slice_ms)
                if _is_logged_in_url(_safe_url(page)):
                    return

        # If nothing happened, yield a bit to allow the page to update.
        with suppress(Exception):
            page.wait_for_timeout(250)

    raise LoginTimeoutError(
        "Login did not complete in time. Complete authentication in the opened browser window."
    )


def _safe_url(page: Page) -> str:
    try:
        return (page.url or "").strip()
    except Exception:
        return ""


def _is_logged_in_url(url: str) -> bool:
    lowered = url.lower()
    return (
        "linkedin.com/feed" in lowered
        and "/checkpoint" not in lowered
        and "/login" not in lowered
        and "/authwall" not in lowered
        and "linkedin.com/uas/" not in lowered
    )


def _is_checkpoint_url(url: str) -> bool:
    lowered = url.lower()
    return "/checkpoint" in lowered or "/challenge" in lowered


def _is_linkedin_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
        return host.endswith("linkedin.com") or host.endswith("www.linkedin.com")
    except Exception:
        return False


def _looks_like_checkpoint_page(page: Page) -> bool:
    # Keep selectors conservative and LinkedIn-specific.
    try:
        return (
            page.locator(
                "form[action*='checkpoint'], input[name='challengeId'], input[name='pin']"
            ).count()
            > 0
        )
    except Exception:
        return False

