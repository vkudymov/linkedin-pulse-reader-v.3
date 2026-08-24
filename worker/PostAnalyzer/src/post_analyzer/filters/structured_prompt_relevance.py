from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..async_llm_post_analyzer import BaseAsyncLLMClient, PostRelevanceAnalyzer, run_async
from .relevance import RelevanceResult


@dataclass(frozen=True, slots=True)
class StructuredPromptRelevanceFilter:
    llm_client: BaseAsyncLLMClient
    prompt_path: str | Path | None = None
    prompt_template: str | None = None
    min_score: int = 70

    def check(self, post: Mapping[str, Any]) -> RelevanceResult:
        if (self.prompt_path is None) == (self.prompt_template is None):
            return RelevanceResult(
                relevant=False,
                error="StructuredPromptRelevanceFilter misconfigured: provide exactly one of prompt_path or prompt_template.",
            )

        text = post.get("text")
        post_url = post.get("post_url")

        if not isinstance(text, str) or not text.strip():
            return RelevanceResult(relevant=False, error="Post is missing non-empty 'text'.")
        if not isinstance(post_url, str) or not post_url.strip():
            return RelevanceResult(relevant=False, error="Post is missing non-empty 'post_url'.")

        try:
            analyzer = PostRelevanceAnalyzer(
                self.llm_client,
                prompt_file=self.prompt_path,
                prompt_template=self.prompt_template,
            )
            r = run_async(analyzer.analyze_post_text(text))
            relevant = bool(r.relevant) and int(r.score) >= int(self.min_score)
            return RelevanceResult(
                relevant=relevant,
                error=None,
                score=int(r.score),
                content_type=r.content_type,
                main_topics=list(r.main_topics),
                reason=r.reason,
                selection_reason=r.selection_reason,
                analysis=dict(r.raw),
            )
        except Exception as e:  # noqa: BLE001 - boundary normalize to string
            return RelevanceResult(relevant=False, error=f"Structured relevance check failed: {e}")

