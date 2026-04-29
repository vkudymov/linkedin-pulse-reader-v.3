from __future__ import annotations

from typing import Any

from .config import PostAnalyzerConfig
from .filters.relevance import RelevanceFilter
from .llm import LLMClient
from .llm_manager import LLMProviderManager
from .log import logger


class LLMPostSelector:
    """Select relevant posts using an LLM, without coupling to any data source.

    This class is intentionally thin: it delegates LLM lifecycle to
    `LLMProviderManager` and keeps business logic in `RelevanceFilter`.
    """

    def __init__(
        self,
        *,
        analyzer_config: PostAnalyzerConfig,
        llm_manager: LLMProviderManager | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._analyzer_config = analyzer_config
        self._llm_manager = llm_manager
        self._llm_client = llm_client
        self._filter: RelevanceFilter | None = None

    def _initialize(self) -> None:
        if self._filter is not None:
            return

        if self._llm_manager is None:
            if self._llm_client is not None:
                # Backward-compatible path: caller supplies an already-built client.
                class _StaticManager:
                    def __init__(self, client: LLMClient) -> None:
                        self._client = client

                    def complete(self, *, system: str | None, user: str) -> str:
                        return self._client.complete(system=system, user=user)

                self._llm_manager = _StaticManager(self._llm_client)  # type: ignore[assignment]
                logger.info("LLMPostSelector initialized with external llm_client.")
            else:
                self._llm_manager = LLMProviderManager.from_env()
                logger.info("LLMPostSelector initialized LLM manager from env.")

        self._filter = RelevanceFilter(llm_client=self._llm_manager, config=self._analyzer_config)

    def select(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return only posts that passed LLM relevance check."""
        self._initialize()
        assert self._filter is not None

        selected: list[dict[str, Any]] = []
        for post in posts:
            res = self._filter.check(post)
            if res.error is None and res.relevant:
                selected.append(post)
        return selected

