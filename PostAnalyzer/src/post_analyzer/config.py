from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PostAnalyzerConfig:
    relevance_system_prompt: str | None
    relevance_user_prompt: str

    comment_system_prompt: str | None
    comment_user_prompt: str

    def format_relevance_user(self, *, text: str, post_url: str) -> str:
        return self.relevance_user_prompt.format(text=text, post_url=post_url)

    def format_comment_user(self, *, text: str, post_url: str) -> str:
        return self.comment_user_prompt.format(text=text, post_url=post_url)


LLMProviderName = Literal["openai", "ollama", "fake"]
LLMMode = Literal["real", "fake"]


@dataclass(frozen=True, slots=True)
class LLMProviderSettings:
    provider: LLMProviderName
    model: str | None = None
    mode: LLMMode = "real"

    base_url: str | None = None
    api_key: str | None = None
    timeout_s: float = 30.0


@dataclass(frozen=True, slots=True)
class LLMManagerSettings:
    primary: LLMProviderSettings
    fallback: LLMProviderSettings | None = None

    enable_fallback: bool = True
    failover_to_fallback: bool = True
    healthcheck_on_switch: bool = True


def load_llm_manager_settings_from_env() -> LLMManagerSettings:
    """Load LLM runtime settings from env vars.

    Backward-compatibility env vars are supported (e.g. OPENAI_API_KEY, OLLAMA_BASE_URL).
    """

    primary = _load_provider_settings_from_env(prefix="POST_ANALYZER_LLM_")
    fallback_provider = os.getenv("POST_ANALYZER_LLM_FALLBACK_PROVIDER")
    fallback = (
        _load_provider_settings_from_env(prefix="POST_ANALYZER_LLM_FALLBACK_", provider_override=fallback_provider)
        if fallback_provider
        else None
    )

    enable_fallback = _env_bool("POST_ANALYZER_LLM_ENABLE_FALLBACK", default=True)
    failover_to_fallback = _env_bool("POST_ANALYZER_LLM_FAILOVER_TO_FALLBACK", default=True)
    healthcheck_on_switch = _env_bool("POST_ANALYZER_LLM_HEALTHCHECK_ON_SWITCH", default=True)

    return LLMManagerSettings(
        primary=primary,
        fallback=fallback,
        enable_fallback=enable_fallback,
        failover_to_fallback=failover_to_fallback,
        healthcheck_on_switch=healthcheck_on_switch,
    )


def _load_provider_settings_from_env(
    *,
    prefix: str,
    provider_override: str | None = None,
) -> LLMProviderSettings:
    provider = (provider_override or os.getenv(f"{prefix}PROVIDER") or "fake").strip().lower()
    if provider not in {"openai", "ollama", "fake"}:
        provider = "fake"

    mode = (os.getenv(f"{prefix}MODE") or "real").strip().lower()
    if mode not in {"real", "fake"}:
        mode = "real"

    model = os.getenv(f"{prefix}MODEL")
    timeout_s = _env_float(f"{prefix}TIMEOUT_S", default=30.0)

    if provider == "openai":
        api_key = os.getenv("POST_ANALYZER_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("POST_ANALYZER_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        if model is None:
            model = os.getenv("POST_ANALYZER_OPENAI_MODEL") or os.getenv("OPENAI_MODEL")
        return LLMProviderSettings(
            provider="openai",
            mode=mode,  # type: ignore[arg-type]
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_s=timeout_s,
        )

    if provider == "ollama":
        base_url = (
            os.getenv("POST_ANALYZER_OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_BASE_URL")
            or os.getenv("OLLAMA_HOST")
        )
        if model is None:
            model = os.getenv("POST_ANALYZER_OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL")
        return LLMProviderSettings(
            provider="ollama",
            mode=mode,  # type: ignore[arg-type]
            model=model,
            base_url=base_url,
            timeout_s=timeout_s,
        )

    # fake
    return LLMProviderSettings(
        provider="fake",
        mode="fake",
        model=model,
        timeout_s=timeout_s,
    )


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_float(name: str, *, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default

