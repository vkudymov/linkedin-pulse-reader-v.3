from __future__ import annotations

import asyncio

import pytest

from post_analyzer.async_llm_post_analyzer import FakeAsyncLLMClient
from post_analyzer.filters.structured_prompt_relevance import StructuredPromptRelevanceFilter


def test_structured_filter_fake_relevant(tmp_path):
    prompt = tmp_path / "prompt.prompt"
    prompt.write_text("Text:\n<<<POST_TEXT>>>", encoding="utf-8")

    f = StructuredPromptRelevanceFilter(
        llm_client=FakeAsyncLLMClient(),
        prompt_path=prompt,
        min_score=70,
    )
    res = f.check({"text": "hello", "post_url": "https://x"})
    assert res.error is None
    assert res.relevant is True
    assert res.score == 80
    assert res.analysis is not None


def test_structured_filter_from_running_event_loop(tmp_path):
    prompt = tmp_path / "prompt.prompt"
    prompt.write_text("Text:\n<<<POST_TEXT>>>", encoding="utf-8")

    f = StructuredPromptRelevanceFilter(
        llm_client=FakeAsyncLLMClient(),
        prompt_path=prompt,
        min_score=70,
    )

    async def _run():
        await asyncio.sleep(0)
        return f.check({"text": "hello", "post_url": "https://x"})

    res = asyncio.run(_run())
    assert res.relevant is True

