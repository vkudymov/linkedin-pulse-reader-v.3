from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import PostAnalyzerConfig
from .generators.comment_prompt_file import (
    CommentPromptContext,
    fill_comment_prompt,
    load_prompt_template,
)
from .llm import LLMClient
from .llm_manager import LLMProviderManager
from .log import logger

POST_SEARCH_MARKER = "<<<POST_TEXT>>>"


class LLMPostSelector:
    """Select relevant posts using the shared JobSearch match analyzer."""

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
        if self._llm_manager is None:
            if self._llm_client is not None:
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

        if self._filter is not None:
            logger.info("LLMPostSelector ignoring injected relevance_filter; using analyze_template.")

    def _get_comment_prompt_template(self) -> str:
        if self._comment_prompt_template is None:
            inline = self._analyzer_config.comment_prompt_template
            if inline is not None:
                self._comment_prompt_template = (inline or "").strip()
            else:
                prompt_path = self._analyzer_config.comment_prompt_path
                if prompt_path is None:
                    raise ValueError("comment prompt is not configured")
                self._comment_prompt_template = load_prompt_template(Path(prompt_path))
        return self._comment_prompt_template

    def analyze(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Annotate every post with match result and optional LLM comment."""
        from job_search.adapters.llm_job_analyzer import analyze_template  # type: ignore[import-not-found]
        from job_search.analysis import match_result_to_payload  # type: ignore[import-not-found]

        self._initialize()
        assert self._llm_manager is not None

        template = (self._analyzer_config.search_prompt_template or "").strip()
        if not template:
            raise ValueError("search_prompt_template is empty")
        marker = (self._analyzer_config.search_marker or POST_SEARCH_MARKER).strip() or POST_SEARCH_MARKER

        for post in posts:
            text = post.get("text") if isinstance(post, dict) else None
            post_text = text if isinstance(text, str) else ""
            try:
                result = analyze_template(
                    llm_client=self._llm_manager,
                    template=template,
                    marker=marker,
                    body_text=post_text,
                )
                payload = match_result_to_payload(result)
                accepted = bool(result.match)
                post["result"] = "принято" if accepted else "отклонено"
                post["reason"] = result.reason
                post["relevance_analysis"] = payload
                post.pop("analysis_error", None)
            except Exception as e:  # noqa: BLE001 - library boundary normalize to string
                accepted = False
                post["result"] = "отклонено"
                post["reason"] = str(e)
                post["analysis_error"] = str(e)
                post["relevance_analysis"] = None
                continue

            needs_comment = (
                self._analyzer_config.comment_prompt_template is not None
                or self._analyzer_config.comment_prompt_path is not None
            )
            if accepted and needs_comment:
                raw = result.raw_payload if isinstance(result.raw_payload, dict) else {}
                content_type = raw.get("content_type")
                main_topics = raw.get("main_topics")
                try:
                    template_comment = self._get_comment_prompt_template()
                    ctx = CommentPromptContext(
                        post_text=post_text,
                        content_type=content_type if isinstance(content_type, str) else "общий",
                        main_topics=(
                            [x for x in main_topics if isinstance(x, str)]
                            if isinstance(main_topics, list)
                            else []
                        ),
                        target_language=self._analyzer_config.comment_target_language,
                    )
                    user = fill_comment_prompt(template_comment, ctx=ctx)
                    raw_comment = self._llm_manager.complete(
                        system=(
                            self._analyzer_config.comment_system_prompt
                            or "Сгенерируй комментарий. Только текст, без markdown и пояснений."
                        ),
                        user=user,
                    )
                    if not (comment := (raw_comment or "").strip()):
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
