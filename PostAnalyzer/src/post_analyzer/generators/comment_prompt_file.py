from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CommentPromptContext:
    post_text: str
    content_type: str
    main_topics: list[str]
    target_language: str


_REQUIRED_MARKERS = (
    "<<<POST_TEXT>>>",
    "<<<CONTENT_TYPE>>>",
    "<<<MAIN_TOPICS>>>",
    "<<<TARGET_LANGUAGE>>>",
)


def load_prompt_template(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Prompt file not found: {p}")
    return p.read_text(encoding="utf-8").strip()


def fill_comment_prompt(template: str, *, ctx: CommentPromptContext) -> str:
    for m in _REQUIRED_MARKERS:
        if m not in template:
            raise ValueError(f"Comment prompt must contain marker {m!r}")

    topics = ", ".join([t.strip() for t in ctx.main_topics if t and t.strip()]) or "—"
    content_type = (ctx.content_type or "").strip() or "general"
    target_language = (ctx.target_language or "").strip() or "ru"
    if not (post_text := (ctx.post_text or "").strip()):
        raise ValueError("Post text cannot be empty")

    return (
        template.replace("<<<CONTENT_TYPE>>>", content_type)
        .replace("<<<MAIN_TOPICS>>>", topics)
        .replace("<<<TARGET_LANGUAGE>>>", target_language)
        .replace("<<<POST_TEXT>>>", post_text)
    )

