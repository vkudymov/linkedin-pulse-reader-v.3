from __future__ import annotations

from post_analyzer import LLMPostSelector, PostAnalyzerConfig


class _TestLLM:
    def complete(self, *, system: str | None, user: str) -> str:
        u = (user or "").lower()
        if "matched_requirements" in u or "<<<post_text>>>" in u or "cds" in u:
            return (
                '{"match":true,"score":80,"reason":"SAP CDS",'
                '"matched_requirements":["CDS"],"missing_requirements":[],"red_flags":[]}'
            )
        if "сгенерируй комментарий" in u or "<<<target_language>>>" in u or "тип контента" in u:
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
        relevance_system_prompt="Return ONLY valid JSON.",
        relevance_user_prompt="unused: {post_url} {text}",
        comment_system_prompt=None,
        comment_user_prompt="unused",
        comment_prompt_path=str(prompt),
        comment_target_language="ru",
        search_prompt_template=(
            "Return JSON with match, score, reason, matched_requirements, "
            "missing_requirements, red_flags.\n<<<POST_TEXT>>>"
        ),
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
    assert selected[0].get("relevance_analysis", {}).get("score") == 80
    assert selected[0].get("comment_error") is None
