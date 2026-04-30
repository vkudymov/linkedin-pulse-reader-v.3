#!/usr/bin/env python3
"""Минимальный запуск LinkedInClient из корня проекта."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LINKEDIN_SRC = ROOT / "LinkedInClient" / "src"
POST_ANALYZER_SRC = ROOT / "PostAnalyzer" / "src"
COOKIES_PATH = ROOT / "cookies.json"
POSTS_PATH = ROOT / "posts.json"
SELECTED_POSTS_PATH = ROOT / "selected_posts.json"

if str(LINKEDIN_SRC) not in sys.path:
    sys.path.insert(0, str(LINKEDIN_SRC))
if str(POST_ANALYZER_SRC) not in sys.path:
    sys.path.insert(0, str(POST_ANALYZER_SRC))

from linkedin_client import LinkedInClient, LinkedInClientConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.browser import BrowserConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.exceptions import LoginRequiredError  # type: ignore[import-not-found]  # noqa: E402

from post_analyzer import LLMPostSelector, PostAnalyzerConfig  # type: ignore[import-not-found]  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

def load_cookies(path: Path) -> list[dict[str, Any]] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array of cookies in {path}")
    return data


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def default_post_analyzer_config() -> PostAnalyzerConfig:
    return PostAnalyzerConfig(
        relevance_system_prompt=(
            "Return strict JSON only. Use schema: {\"relevant\": true|false}."
        ),
        relevance_user_prompt=(
            "Post URL:\n{post_url}\n\nPost text:\n{text}\n\n"
            "Reply with strict JSON only: {{\"relevant\": true|false}}"
        ),
        comment_system_prompt=None,
        comment_user_prompt="unused: {post_url} {text}",
    )

def to_analyzer_row(post: dict[str, Any]) -> dict[str, Any]:
    text = post.get("content")
    post_url = post.get("post_url")
    return {
        **post,
        "text": (text or "").strip() if isinstance(text, str) else "",
        "post_url": (post_url or "").strip() if isinstance(post_url, str) else "",
    }


def post_to_dict(post: Any) -> dict[str, Any]:
    author = getattr(post, "author", None)
    return {
        "urn": getattr(post, "urn", None),
        "post_url": getattr(post, "post_url", None),
        "published_at_text": getattr(post, "published_at_text", None),
        "content": getattr(post, "content", None),
        "reactions_count": getattr(post, "reactions_count", None),
        "comments_count": getattr(post, "comments_count", None),
        "media_urls": list(getattr(post, "media_urls", []) or []),
        "author": (
            None
            if author is None
            else {
                "name": getattr(author, "name", None),
                "headline": getattr(author, "headline", None),
                "profile_url": getattr(author, "profile_url", None),
                "urn": getattr(author, "urn", None),
            }
        ),
    }


def login_and_save_cookies(cfg: LinkedInClientConfig) -> list[dict[str, Any]]:
    log.info("Cookies missing or expired. Log in in the opened browser window.")
    with LinkedInClient(config=cfg) as client:
        cookies = client.login_and_get_cookies()
    save_json(COOKIES_PATH, cookies)
    log.info("Saved %s cookies to %s", len(cookies), COOKIES_PATH)
    return cookies


def fetch_and_save_posts(
    cookies: list[dict[str, Any]], cfg: LinkedInClientConfig, limit: int
) -> None:
    log.info("Fetching posts: limit=%s", limit)
    with LinkedInClient(cookies=cookies, config=cfg) as client:
        posts = client.fetch_posts(limit=limit)
        fresh_cookies = client.get_cookies()
        save_json(COOKIES_PATH, fresh_cookies)

    payload = [post_to_dict(post) for post in posts]
    save_json(POSTS_PATH, payload)
    log.info("Saved %s posts to %s", len(posts), POSTS_PATH)
    log.info("Updated cookies in %s", COOKIES_PATH)

    analyzer_input = [to_analyzer_row(p) for p in payload]
    try:
        from post_analyzer.config import load_llm_manager_settings_from_env  # type: ignore[import-not-found]
        from post_analyzer.config import LLMProviderSettings  # type: ignore[import-not-found]
        from post_analyzer.llm_manager import LLMProviderManager  # type: ignore[import-not-found]
        settings = load_llm_manager_settings_from_env()
        mgr = LLMProviderManager(settings=settings)
        desc = mgr.describe()

        # If env is not configured, PostAnalyzer defaults to fake/fake.
        # For the demo we prefer a real provider; attempt to switch to local Ollama.
        if desc.get("provider") == "fake" and desc.get("mode") == "fake":
            ollama_base_url = (
                os.getenv("POST_ANALYZER_OLLAMA_BASE_URL")
                or os.getenv("OLLAMA_BASE_URL")
                or os.getenv("OLLAMA_HOST")
                or "http://localhost:11434"
            )
            ollama_model = (
                os.getenv("POST_ANALYZER_LLM_MODEL")
                or os.getenv("POST_ANALYZER_OLLAMA_MODEL")
                or os.getenv("OLLAMA_MODEL")
                or "llama3.1:8b"
            )
            mgr.switch(
                primary=LLMProviderSettings(
                    provider="ollama",
                    mode="real",
                    model=ollama_model,
                    base_url=ollama_base_url,
                ),
                fallback=None,
            )
    except Exception as e:
        log.error(
            "LLM is not configured. Set POST_ANALYZER_LLM_PROVIDER=ollama (or openai) "
            "and ensure Ollama is running on http://localhost:11434."
        )
        mgr = None

    selector = (
        LLMPostSelector(analyzer_config=default_post_analyzer_config(), llm_manager=mgr)
        if mgr is not None
        else LLMPostSelector(analyzer_config=default_post_analyzer_config())
    )

    selected = selector.select(analyzer_input)
    save_json(SELECTED_POSTS_PATH, selected)
    log.info(
        "Saved %s selected posts to %s", len(selected), SELECTED_POSTS_PATH
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch LinkedIn posts via LinkedInClient."
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    log.info(
        "Starting LinkedInClient demo: limit=%s headless=%s", args.limit, args.headless
    )
    cfg = LinkedInClientConfig(
        browser=BrowserConfig(headless=args.headless, timeout_ms=60_000)
    )
    cookies = load_cookies(COOKIES_PATH)

    if cookies is None:
        cookies = login_and_save_cookies(cfg)
    else:
        log.info("Loaded %s cookies from %s", len(cookies), COOKIES_PATH)

    try:
        fetch_and_save_posts(cookies, cfg, args.limit)
    except LoginRequiredError:
        log.info("Stored cookies are expired. Re-login and retry once.")
        fetch_and_save_posts(login_and_save_cookies(cfg), cfg, args.limit)
    except Exception:
        log.exception("LinkedInClient demo failed")
        raise


if __name__ == "__main__":
    main()
