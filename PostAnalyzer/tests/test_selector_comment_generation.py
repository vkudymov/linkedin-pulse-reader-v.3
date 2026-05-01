from __future__ import annotations

import pytest

from post_analyzer import LLMPostSelector, PostAnalyzerConfig


class _TestLLM:
    def complete(self, *, system: str | None, user: str) -> str:
        u = (user or "").lower()
        if "reply with strict json only" in u or '"relevant"' in u:
            return '{"relevant": true}'
        if "сгенерируй комментарий" in u:
            return "Хороший разбор. Особенно важно учитывать производительность и качество данных на практике."
        return "ok"


def test_selector_adds_comment_from_file_prompt(tmp_path):
    prompt = tmp_path / "linkedin_comment_generation.prompt"
    prompt.write_text(
        "\n".join(
            [
                "Тип контента: <<<CONTENT_TYPE>>>",
                "Ключевые темы: <<<MAIN_TOPICS>>>",
                "Язык комментария: <<<TARGET_LANGUAGE>>>",
                "",
                "Текст поста:",
                "<<<POST_TEXT>>>",
                "",
                "Сгенерируй комментарий на языке <<<TARGET_LANGUAGE>>> (только текст, без префиксов и пояснений):",
            ]
        ),
        encoding="utf-8",
    )

    cfg = PostAnalyzerConfig(
        relevance_system_prompt="Return strict JSON only. Use schema: {\"relevant\": true|false}.",
        relevance_user_prompt=(
            "Post URL:\n{post_url}\n\nPost text:\n{text}\n\n"
            "Reply with strict JSON only: {{\"relevant\": true|false}}"
        ),
        comment_system_prompt=None,
        comment_user_prompt="unused",
        comment_prompt_path=str(prompt),
        comment_target_language="ru",
    )

    selector = LLMPostSelector(analyzer_config=cfg, llm_client=_TestLLM())
    selected = selector.select(
        [
            {
                "text": "Пост про SAP HANA и оптимизацию CDS View.",
                "post_url": "https://example.com/post/1",
            }
        ]
    )

    assert len(selected) == 1
    assert selected[0].get("comment")
    assert selected[0]["comment_error"] if "comment_error" in selected[0] else None is None

