from __future__ import annotations

from dataclasses import replace
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from .config import LLMManagerSettings, LLMProviderSettings, load_llm_manager_settings_from_env
from .llm import LLMClient
from .llm_errors import LLMConfigError, LLMConnectionError, LLMSwitchError
from .llm_factory import LLMFactory
from .log import logger


class LLMProviderManager:
    """Runtime-switchable LLM client manager with rollback and optional fallback."""

    def __init__(
        self,
        *,
        settings: LLMManagerSettings,
        factory: LLMFactory | None = None,
        healthcheck_on_init: bool = False,
    ) -> None:
        self._lock = RLock()
        self._factory = factory or LLMFactory()

        self._settings = settings
        self._validate_settings(settings)

        self._primary_client = self._factory.create_client(settings.primary)
        self._fallback_client = (
            self._factory.create_client(settings.fallback)
            if settings.enable_fallback and settings.fallback is not None
            else None
        )
        self._active = "primary"

        logger.info(
            "LLM manager initialized provider=%s model=%s mode=%s fallback=%s",
            settings.primary.provider,
            settings.primary.model,
            settings.primary.mode,
            settings.fallback.provider if settings.fallback else None,
        )

        if healthcheck_on_init and settings.primary.mode == "real":
            self.test_connection()

    @classmethod
    def from_env(
        cls,
        *,
        factory: LLMFactory | None = None,
        healthcheck_on_init: bool = False,
    ) -> LLMProviderManager:
        settings = load_llm_manager_settings_from_env()
        return cls(settings=settings, factory=factory, healthcheck_on_init=healthcheck_on_init)

    def describe(self) -> dict[str, Any]:
        with self._lock:
            active_settings = self._settings.primary if self._active == "primary" else self._settings.fallback
            return {
                "active": self._active,
                "provider": active_settings.provider if active_settings else None,
                "model": active_settings.model if active_settings else None,
                "mode": active_settings.mode if active_settings else None,
                "has_fallback": self._settings.fallback is not None and self._settings.enable_fallback,
            }

    def test_connection(self) -> None:
        """Health-check the currently active client (real mode only)."""
        with self._lock:
            settings = self._settings.primary if self._active == "primary" else self._settings.fallback
            client = self._primary_client if self._active == "primary" else self._fallback_client

        if settings is None or client is None:
            raise LLMConnectionError("No active LLM client configured.")
        if settings.mode != "real":
            logger.info("Skipping health-check (mode=%s).", settings.mode)
            return None

        try:
            test_fn = getattr(client, "test_connection", None)
            if callable(test_fn):
                test_fn()
            else:
                _ = client.complete(system=None, user="Reply with exactly: ok")
        except Exception as e:
            logger.exception(
                "LLM health-check failed provider=%s model=%s: %s",
                settings.provider,
                settings.model,
                e,
            )
            raise LLMConnectionError(f"LLM health-check failed: {e}") from e

        logger.info(
            "LLM health-check OK provider=%s model=%s",
            settings.provider,
            settings.model,
        )
        return None

    def switch(
        self,
        *,
        primary: LLMProviderSettings,
        fallback: LLMProviderSettings | None = None,
    ) -> None:
        """Switch provider/model at runtime with validation, health-check and rollback."""
        with self._lock:
            prev_settings = self._settings
            prev_primary_client = self._primary_client
            prev_fallback_client = self._fallback_client
            prev_active = self._active

            next_settings = replace(
                prev_settings,
                primary=primary,
                fallback=fallback,
            )

            try:
                self._validate_settings(next_settings)

                next_primary_client = self._factory.create_client(next_settings.primary)
                next_fallback_client = (
                    self._factory.create_client(next_settings.fallback)
                    if next_settings.enable_fallback and next_settings.fallback is not None
                    else None
                )

                if next_settings.healthcheck_on_switch and next_settings.primary.mode == "real":
                    self._healthcheck_client(next_primary_client, next_settings.primary)

                # commit
                self._settings = next_settings
                self._primary_client = next_primary_client
                self._fallback_client = next_fallback_client
                self._active = "primary"

                logger.info(
                    "LLM switched provider=%s model=%s mode=%s fallback=%s",
                    next_settings.primary.provider,
                    next_settings.primary.model,
                    next_settings.primary.mode,
                    next_settings.fallback.provider if next_settings.fallback else None,
                )
            except Exception as e:
                # rollback
                self._settings = prev_settings
                self._primary_client = prev_primary_client
                self._fallback_client = prev_fallback_client
                self._active = prev_active

                logger.exception("LLM switch failed; rolled back: %s", e)
                raise LLMSwitchError(str(e)) from e

    def complete(self, *, system: str | None, user: str) -> str:
        """LLMClient-compatible entrypoint with optional fallback failover."""
        with self._lock:
            active = self._active
            active_client = self._primary_client if active == "primary" else self._fallback_client
            active_settings = self._settings.primary if active == "primary" else self._settings.fallback
            fallback_client = self._fallback_client
            fallback_settings = self._settings.fallback
            enable_fallback = self._settings.enable_fallback
            failover = self._settings.failover_to_fallback

        if active_client is None or active_settings is None:
            raise LLMConnectionError("Active LLM client is not configured.")

        try:
            return active_client.complete(system=system, user=user)
        except Exception as e:
            logger.exception(
                "LLM call failed provider=%s model=%s active=%s: %s",
                active_settings.provider,
                active_settings.model,
                active,
                e,
            )

            if not enable_fallback or fallback_client is None or fallback_settings is None:
                raise

            logger.warning(
                "Trying fallback provider=%s model=%s due to error: %s",
                fallback_settings.provider,
                fallback_settings.model,
                e,
            )

            try:
                result = fallback_client.complete(system=system, user=user)
            except Exception as e2:
                logger.exception(
                    "Fallback LLM call also failed provider=%s model=%s: %s",
                    fallback_settings.provider,
                    fallback_settings.model,
                    e2,
                )
                raise

            if failover:
                with self._lock:
                    self._active = "fallback"
                logger.warning(
                    "Failover: active LLM is now fallback provider=%s model=%s",
                    fallback_settings.provider,
                    fallback_settings.model,
                )

            return result

    def _healthcheck_client(self, client: LLMClient, settings: LLMProviderSettings) -> None:
        try:
            test_fn = getattr(client, "test_connection", None)
            if callable(test_fn):
                test_fn()
            else:
                _ = client.complete(system=None, user="Reply with exactly: ok")
        except Exception as e:
            raise LLMConnectionError(
                f"Health-check failed for provider={settings.provider} model={settings.model}: {e}"
            ) from e

    def _validate_settings(self, settings: LLMManagerSettings) -> None:
        self._validate_provider(settings.primary)
        if settings.enable_fallback and settings.fallback is not None:
            self._validate_provider(settings.fallback)

    def _validate_provider(self, s: LLMProviderSettings) -> None:
        if s.provider == "fake" or s.mode == "fake":
            return

        if s.provider == "openai":
            if not s.api_key and not _is_local_base_url(s.base_url):
                raise LLMConfigError(
                    "OpenAI: missing api_key (set OPENAI_API_KEY or POST_ANALYZER_OPENAI_API_KEY). "
                    "Key is optional only for localhost base_url (LM Studio)."
                )
            if not s.model:
                raise LLMConfigError("OpenAI: missing model (set POST_ANALYZER_LLM_MODEL / OPENAI_MODEL).")
            return

        if s.provider == "ollama":
            if not s.model:
                raise LLMConfigError("Ollama: missing model (set POST_ANALYZER_LLM_MODEL / OLLAMA_MODEL).")
            return

        raise LLMConfigError(f"Unsupported provider: {s.provider!r}")


def _is_local_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    try:
        hostname = (urlparse(base_url).hostname or "").strip().lower()
    except Exception:
        return False
    return hostname in {"127.0.0.1", "localhost"}

