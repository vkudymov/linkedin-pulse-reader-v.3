from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import PostAnalyzerConfig
from .filters.relevance import RelevanceFilter, RelevanceResult
from .generators.comment_prompt_file import (
    CommentPromptContext,
    fill_comment_prompt,
    load_prompt_template,
)
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
        relevance_filter: Any | None = None,
    ) -> None:
        self._analyzer_config = analyzer_config
        self._llm_manager = llm_manager
        self._llm_client = llm_client
        self._filter: Any | None = relevance_filter
        self._comment_prompt_template: str | None = None

    def _initialize(self) -> None:
        needs_llm_manager = self._filter is None or self._analyzer_config.comment_prompt_path is not None

        if needs_llm_manager and self._llm_manager is None:
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

        if self._filter is None:
            assert self._llm_manager is not None
            self._filter = RelevanceFilter(llm_client=self._llm_manager, config=self._analyzer_config)

    def _get_comment_prompt_template(self) -> str:
        if self._comment_prompt_template is None:
            prompt_path = self._analyzer_config.comment_prompt_path
            if prompt_path is None:
                raise ValueError("comment_prompt_path is not configured")
            self._comment_prompt_template = load_prompt_template(Path(prompt_path))
        return self._comment_prompt_template

    def analyze(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Annotate every post with relevance result and optional LLM reason."""
        self._initialize()
        assert self._filter is not None

        for post in posts:
            res: RelevanceResult = self._filter.check(post)
            accepted = res.error is None and res.relevant
            post["result"] = "принято" if accepted else "отклонено"
            post["reason"] = _result_reason(res)
            if res.error is not None:
                post["analysis_error"] = res.error

            analysis = res.analysis
            if analysis is not None or res.score is not None or res.reason is not None:
                post["relevance_analysis"] = {
                    "relevant": res.relevant,
                    "score": res.score,
                    "content_type": res.content_type,
                    "main_topics": res.main_topics,
                    "reason": res.reason,
                    "selection_reason": res.selection_reason,
                    "analysis": analysis,
                }

            if accepted and self._analyzer_config.comment_prompt_path is not None:
                assert self._llm_manager is not None
                try:
                    template = self._get_comment_prompt_template()
                    text = post.get("text") if isinstance(post, dict) else None
                    post_text = text if isinstance(text, str) else ""
                    ctx = CommentPromptContext(
                        post_text=post_text,
                        content_type=(res.content_type or "общий"),
                        main_topics=list(res.main_topics or []),
                        target_language=self._analyzer_config.comment_target_language,
                    )
                    user = fill_comment_prompt(template, ctx=ctx)
                    raw = self._llm_manager.complete(
                        system=(
                            self._analyzer_config.comment_system_prompt
                            or "Сгенерируй комментарий. Только текст, без markdown и пояснений."
                        ),
                        user=user,
                    )
                    if not (comment := (raw or "").strip()):
                        post["comment"] = None
                        post["comment_error"] = "LLM returned an empty comment."
                    else:
                        post["comment"] = comment
                except Exception as e:  # noqa: BLE001 - library boundary normalize to string
                    post["comment"] = None
                    post["comment_error"] = f"LLM comment generation failed: {e}"

        return posts

    def select(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return only posts that passed LLM relevance check."""
        analyzed = self.analyze(posts)
        return [post for post in analyzed if post.get("result") == "принято"]


def _result_reason(res: RelevanceResult) -> str | None:
    if res.error is not None:
        return res.error
    if res.relevant:
        return res.selection_reason or res.reason
    return res.reason or res.selection_reason

