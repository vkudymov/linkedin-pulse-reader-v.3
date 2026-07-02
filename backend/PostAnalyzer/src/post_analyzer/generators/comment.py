from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..config import PostAnalyzerConfig
from ..llm import LLMClient


@dataclass(frozen=True, slots=True)
class CommentResult:
    comment: str | None
    error: str | None = None


class CommentGenerator:
    def __init__(self, *, llm_client: LLMClient, config: PostAnalyzerConfig) -> None:
        self._llm_client = llm_client
        self._config = config

    def generate(self, post: Mapping[str, Any]) -> CommentResult:
        text = post.get("text")
        post_url = post.get("post_url")

        if not isinstance(text, str) or not text.strip():
            return CommentResult(comment=None, error="Post is missing non-empty 'text'.")
        if not isinstance(post_url, str) or not post_url.strip():
            return CommentResult(comment=None, error="Post is missing non-empty 'post_url'.")

        try:
            raw = self._llm_client.complete(
                system=self._config.comment_system_prompt,
                user=self._config.format_comment_user(text=text, post_url=post_url),
            )
        except Exception as e:  # noqa: BLE001 - library boundary: normalize to string
            return CommentResult(comment=None, error=f"LLM comment generation failed: {e}")

        comment = (raw or "").strip()
        if not comment:
            return CommentResult(comment=None, error="LLM returned an empty comment.")

        return CommentResult(comment=comment, error=None)

