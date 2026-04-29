from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrowserConfig:
    """
    RU: Настройки runtime-окружения браузера (platform policy).
        Держим их отдельно от фич-логики, чтобы управление запуском Chromium было централизованным.

    EN: Browser runtime settings (platform policy).
        Kept separate from feature logic so Chromium startup policy is centralized.
    """
    headless: bool = True
    timeout_ms: int = 30_000

    locale: str | None = "en-US"
    timezone_id: str | None = None
    user_agent: str | None = None

    viewport_width: int = 1365
    viewport_height: int = 768

    slow_mo_ms: int | None = None

