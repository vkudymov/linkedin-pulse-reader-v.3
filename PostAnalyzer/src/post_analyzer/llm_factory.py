from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import LLMProviderSettings
from .llm import LLMClient
from .llm_errors import LLMConfigError, LLMConnectionError


class LLMFactory:
    def create_client(self, settings: LLMProviderSettings) -> LLMClient:
        if settings.provider == "fake" or settings.mode == "fake":
            return FakeLLMClient()
        if settings.provider == "openai":
            return OpenAIChatClient.from_settings(settings)
        if settings.provider == "ollama":
            return OllamaChatClient.from_settings(settings)
        raise LLMConfigError(f"Unsupported provider: {settings.provider!r}")


@dataclass(frozen=True, slots=True)
class OpenAIChatClient:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_s: float = 30.0

    @classmethod
    def from_settings(cls, s: LLMProviderSettings) -> OpenAIChatClient:
        if not s.api_key:
            raise LLMConfigError("OpenAI provider requires an API key.")
        if not s.model:
            raise LLMConfigError("OpenAI provider requires a model name.")
        return cls(
            api_key=s.api_key,
            model=s.model,
            base_url=(s.base_url or "https://api.openai.com/v1").rstrip("/"),
            timeout_s=s.timeout_s,
        )

    def test_connection(self) -> None:
        _ = self.complete(system=None, user="Reply with exactly: ok")

    def complete(self, *, system: str | None, user: str) -> str:
        url = f"{self.base_url}/chat/completions"
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }

        req = urllib.request.Request(
            url,
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            raise LLMConnectionError(f"OpenAI HTTP error: {e.code}. Body: {raw}") from e
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"OpenAI connection error: {e}") from e
        except Exception as e:
            raise LLMConnectionError(f"OpenAI request failed: {e}") from e

        try:
            return (
                payload["choices"][0]["message"]["content"]  # type: ignore[index]
            )
        except Exception as e:
            raise LLMConnectionError(f"Unexpected OpenAI response shape: {payload!r}") from e


@dataclass(frozen=True, slots=True)
class OllamaChatClient:
    model: str
    base_url: str = "http://localhost:11434"
    timeout_s: float = 30.0

    @classmethod
    def from_settings(cls, s: LLMProviderSettings) -> OllamaChatClient:
        if not s.model:
            raise LLMConfigError("Ollama provider requires a model name.")
        return cls(
            model=s.model,
            base_url=(s.base_url or "http://localhost:11434").rstrip("/"),
            timeout_s=s.timeout_s,
        )

    def test_connection(self) -> None:
        _ = self.complete(system=None, user="Reply with exactly: ok")

    def complete(self, *, system: str | None, user: str) -> str:
        url = f"{self.base_url}/api/chat"
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        req = urllib.request.Request(
            url,
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            raise LLMConnectionError(f"Ollama HTTP error: {e.code}. Body: {raw}") from e
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"Ollama connection error: {e}") from e
        except Exception as e:
            raise LLMConnectionError(f"Ollama request failed: {e}") from e

        msg = payload.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
        raise LLMConnectionError(f"Unexpected Ollama response shape: {payload!r}")


class FakeLLMClient:
    """Deterministic client for tests and offline runs."""

    def __init__(self, *, fixed_response: str | None = None) -> None:
        self._fixed_response = fixed_response

    def test_connection(self) -> None:
        return None

    def complete(self, *, system: str | None, user: str) -> str:
        if self._fixed_response is not None:
            return self._fixed_response

        u = (user or "").lower()
        if "relevant" in u and "json" in u:
            return json.dumps({"relevant": False})
        if "comment" in u:
            return "Thanks for sharing—interesting point!"
        return "ok"

