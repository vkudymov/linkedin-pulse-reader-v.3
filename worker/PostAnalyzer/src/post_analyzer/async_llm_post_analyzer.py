from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class BaseAsyncLLMClient(Protocol):
    async def generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str: ...

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_response_size: int = 10_000,
    ) -> Dict[str, Any]: ...

    async def test_connection(self) -> None: ...


class FakeAsyncLLMClient:
    def __init__(self, model: str = "fake-model", timeout: float = 5.0):
        self.model = model
        self.timeout = timeout

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return (
            '{"relevant": true, "score": 80, "content_type": "opinion", '
            '"main_topics": ["test"], "reason": "fake", "selection_reason": "fake mode"}'
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_response_size: int = 10_000,
    ) -> Dict[str, Any]:
        return {
            "relevant": True,
            "score": 80,
            "content_type": "opinion",
            "main_topics": ["test"],
            "reason": "fake",
            "selection_reason": "fake mode",
        }

    async def test_connection(self) -> None:
        return None


class OpenAIAsyncLLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: float = 60.0):
        if not api_key:
            raise ValueError("OpenAI API key is required")
        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "OpenAI client requires extra dependencies. Install: post-analyzer[structured]"
            ) from e

        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,
        )
        text = resp.choices[0].message.content or ""
        if not text.strip():
            raise ValueError("Empty response from OpenAI")
        return text.strip()

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_response_size: int = 10_000,
    ) -> Dict[str, Any]:
        text = await self.generate(prompt, system_prompt)
        if len(text) > max_response_size:
            raise ValueError(f"Response too large: {len(text)} chars")

        json_text = _extract_json_text(text)
        parsed = json.loads(json_text)
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object")
        return parsed

    async def test_connection(self) -> None:
        result = await self.generate_json(
            prompt='{"ping":"pong"}',
            system_prompt="Return JSON unchanged.",
        )
        if result.get("ping") != "pong":
            raise ConnectionError(f"Unexpected healthcheck response: {result}")


class OllamaAsyncLLMClient:
    def __init__(self, base_url: str, model: str, timeout: float = 60.0):
        if not base_url:
            raise ValueError("base_url is required for Ollama")
        if not model:
            raise ValueError("model is required for Ollama")
        try:
            import httpx  # type: ignore[import-not-found]
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Ollama client requires extra dependencies. Install: post-analyzer[structured]"
            ) from e

        self._httpx = httpx
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with self._httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        if not (text := (data.get("response") or "").strip()):
            raise ValueError("Empty response from Ollama")
        return text

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_response_size: int = 10_000,
    ) -> Dict[str, Any]:
        text = await self.generate(prompt, system_prompt)
        if len(text) > max_response_size:
            raise ValueError(f"Response too large: {len(text)} chars")
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object")
        return parsed

    async def test_connection(self) -> None:
        _ = await self.generate("Return exactly: OK")


def create_async_llm_client(
    *,
    provider: str,
    mode: str = "real",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 60.0,
) -> BaseAsyncLLMClient:
    p = provider.lower().strip()
    m = mode.lower().strip()

    if p == "openai":
        if m == "fake":
            return FakeAsyncLLMClient(model=model or "fake-openai", timeout=timeout)
        return OpenAIAsyncLLMClient(
            api_key=api_key or "", model=model or "gpt-4o-mini", timeout=timeout
        )

    if p == "ollama":
        if m == "fake":
            return FakeAsyncLLMClient(model=model or "fake-ollama", timeout=timeout)
        return OllamaAsyncLLMClient(
            base_url=base_url or "http://localhost:11434",
            model=model or "llama3.1:8b",
            timeout=timeout,
        )

    raise ValueError(f"Unknown provider: {provider}. Supported: openai, ollama")


@dataclass(frozen=True, slots=True)
class PostAnalysisResult:
    text: str
    relevant: bool
    score: int
    content_type: str
    main_topics: List[str]
    reason: str
    selection_reason: str
    raw: Dict[str, Any]


class PostRelevanceAnalyzer:
    REQUIRED_FIELDS = [
        "relevant",
        "score",
        "content_type",
        "main_topics",
        "reason",
        "selection_reason",
    ]

    def __init__(
        self,
        llm_client: BaseAsyncLLMClient,
        *,
        prompt_file: str | Path | None = None,
        prompt_template: str | None = None,
    ):
        self._llm_client = llm_client
        if (prompt_file is None) == (prompt_template is None):
            raise ValueError("Provide exactly one of prompt_file or prompt_template.")
        self._prompt_file = Path(prompt_file) if prompt_file is not None else None
        if self._prompt_file is not None and not self._prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {self._prompt_file}")
        self._prompt_template: Optional[str] = (prompt_template or None)

    def _load_prompt(self) -> str:
        if self._prompt_template is None:
            assert self._prompt_file is not None
            self._prompt_template = self._prompt_file.read_text(encoding="utf-8").strip()
        return self._prompt_template

    def _build_prompt(self, post_text: str) -> str:
        template = self._load_prompt()
        if "<<<POST_TEXT>>>" not in template:
            raise ValueError("Prompt must contain <<<POST_TEXT>>> placeholder")
        return template.replace("<<<POST_TEXT>>>", post_text)

    def _validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        for f in self.REQUIRED_FIELDS:
            if f not in data:
                raise ValueError(f"Missing field '{f}' in LLM response: {data}")

        if not isinstance(data["relevant"], bool):
            raise ValueError("'relevant' must be bool")

        score = data["score"]
        if not isinstance(score, (int, float)):
            raise ValueError("'score' must be number")
        data["score"] = max(0, min(100, int(score)))

        if not isinstance(data["content_type"], str):
            raise ValueError("'content_type' must be str")
        if not isinstance(data["main_topics"], list):
            raise ValueError("'main_topics' must be list")
        if not isinstance(data["reason"], str):
            raise ValueError("'reason' must be str")
        if not isinstance(data["selection_reason"], str):
            raise ValueError("'selection_reason' must be str")

        return data

    async def analyze_post_text(self, post_text: str) -> PostAnalysisResult:
        if not post_text or not post_text.strip():
            raise ValueError("Post text cannot be empty")

        prompt = self._build_prompt(post_text)
        system_prompt = (
            "Ты помощник для анализа постов LinkedIn. "
            "Отвечай строго в JSON-формате, без markdown и без лишнего текста."
        )

        raw = await self._llm_client.generate_json(prompt, system_prompt)
        raw = self._validate(raw)

        return PostAnalysisResult(
            text=post_text,
            relevant=raw["relevant"],
            score=raw["score"],
            content_type=raw["content_type"],
            main_topics=raw["main_topics"],
            reason=raw["reason"],
            selection_reason=raw["selection_reason"],
            raw=raw,
        )


def run_async(coro: Any) -> Any:
    """Run an async coroutine from sync code.

    If we're already in an event loop, run in a dedicated thread.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    if not loop.is_running():  # pragma: no cover
        return loop.run_until_complete(coro)

    result: Dict[str, Any] = {}

    def _worker() -> None:
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result["value"] = new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        except BaseException as e:  # noqa: BLE001
            result["error"] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()

    if "error" in result:
        raise result["error"]
    return result.get("value")


def _extract_json_text(text: str) -> str:
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            return text[start:end].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text
