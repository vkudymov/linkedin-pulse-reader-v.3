from __future__ import annotations

from typing import Any, Mapping

from .config import PostAnalyzerConfig
from .filters.relevance import RelevanceFilter
from .generators.comment import CommentGenerator
from .llm import LLMClient
from .types import AnalysisItem


class PostAnalyzer:
    def __init__(
        self,
        *,
        llm_client: LLMClient,
        config: PostAnalyzerConfig,
        relevance_filter: RelevanceFilter | None = None,
        comment_generator: CommentGenerator | None = None,
    ) -> None:
        self._relevance_filter = relevance_filter or RelevanceFilter(
            llm_client=llm_client, config=config
        )
        self._comment_generator = comment_generator or CommentGenerator(
            llm_client=llm_client, config=config
        )

    def analyze(self, posts: list[dict[str, Any]]) -> list[AnalysisItem]:
        results: list[AnalysisItem] = []

        for post in posts:
            if not isinstance(post, Mapping):
                results.append(
                    {
                        "post_url": "",
                        "is_relevant": False,
                        "comment": None,
                        "error": "Post must be a dict-like mapping.",
                    }
                )
                continue

            post_url_value = post.get("post_url")
            post_url = post_url_value if isinstance(post_url_value, str) else ""

            relevance = self._relevance_filter.check(post)
            if relevance.error is not None:
                results.append(
                    {
                        "post_url": post_url,
                        "is_relevant": False,
                        "comment": None,
                        "error": relevance.error,
                    }
                )
                continue

            if not relevance.relevant:
                results.append(
                    {
                        "post_url": post_url,
                        "is_relevant": False,
                        "comment": None,
                        "error": None,
                    }
                )
                continue

            comment = self._comment_generator.generate(post)
            if comment.error is not None:
                results.append(
                    {
                        "post_url": post_url,
                        "is_relevant": False,
                        "comment": None,
                        "error": comment.error,
                    }
                )
                continue

            results.append(
                {
                    "post_url": post_url,
                    "is_relevant": True,
                    "comment": comment.comment,
                    "error": None,
                }
            )

        return results

