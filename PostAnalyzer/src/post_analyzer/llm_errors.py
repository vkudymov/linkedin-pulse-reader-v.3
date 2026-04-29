from __future__ import annotations


class LLMError(Exception):
    """Base error for LLM integration."""


class LLMConfigError(LLMError):
    """Invalid configuration for a provider/model."""


class LLMConnectionError(LLMError):
    """Provider is unreachable or returned an error response."""


class LLMSwitchError(LLMError):
    """Switching provider/model failed and was rolled back."""

