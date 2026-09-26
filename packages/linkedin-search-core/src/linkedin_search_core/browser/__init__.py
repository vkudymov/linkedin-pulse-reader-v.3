"""
RU: Platform/browser layer.
    Инкапсулирует lifecycle Playwright/Chromium и runtime-настройки браузера.

EN: Platform/browser layer.
    Encapsulates Playwright/Chromium lifecycle and browser runtime configuration.
"""

from .config import BrowserConfig
from .manager import BrowserManager

__all__ = ["BrowserConfig", "BrowserManager"]

