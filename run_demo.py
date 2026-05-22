#!/usr/bin/env python3
"""Минимальный запуск LinkedInClient из корня проекта."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LINKEDIN_SRC = ROOT / "LinkedInClient" / "src"
POST_ANALYZER_SRC = ROOT / "PostAnalyzer" / "src"
STORAGE_SRC = ROOT / "Storage" / "src"
POSTS_PATH = ROOT / "posts.json"
SELECTED_POSTS_PATH = ROOT / "selected_posts.json"
ENV_PATH = ROOT / ".env"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(ENV_PATH)

if str(LINKEDIN_SRC) not in sys.path:
    sys.path.insert(0, str(LINKEDIN_SRC))
if str(POST_ANALYZER_SRC) not in sys.path:
    sys.path.insert(0, str(POST_ANALYZER_SRC))
if str(STORAGE_SRC) not in sys.path:
    sys.path.insert(0, str(STORAGE_SRC))

from linkedin_client import LinkedInClient, LinkedInClientConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.browser import BrowserConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.exceptions import LoginRequiredError  # type: ignore[import-not-found]  # noqa: E402

from post_analyzer import LLMPostSelector, PostAnalyzerConfig  # type: ignore[import-not-found]  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def log_supabase_target() -> None:
    try:
        from urllib.parse import urlparse

        url = (os.getenv("SUPABASE_URL") or "").strip()
        host = urlparse(url).hostname or ""
        log.info("Supabase storage enabled. Target host=%s", host or "<missing>")
    except Exception:
        log.info("Supabase storage enabled.")


def make_run_timestamp() -> str:
    return datetime.now().astimezone().isoformat()


def write_run_snapshot(path: Path, *, run_at: str, posts: list[dict[str, Any]]) -> None:
    payload: dict[str, Any] = {"run_at": run_at, "count": len(posts), "posts": posts}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def default_post_analyzer_config() -> PostAnalyzerConfig:
    comment_prompt_path = (
        ROOT / "PostAnalyzer" / "prompts" / "linkedin_comment_generation.prompt"
    )
    return PostAnalyzerConfig(
        relevance_system_prompt=(
            'Return strict JSON only. Use schema: {"relevant": true|false}.'
        ),
        relevance_user_prompt=(
            "Post URL:\n{post_url}\n\nPost text:\n{text}\n\n"
            'Reply with strict JSON only: {{"relevant": true|false}}'
        ),
        comment_system_prompt=None,
        comment_user_prompt="unused: {post_url} {text}",
        comment_prompt_path=str(comment_prompt_path),
        comment_target_language=os.getenv("POST_ANALYZER_COMMENT_LANGUAGE", "ru"),
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


def login_and_get_cookies(cfg: LinkedInClientConfig) -> list[dict[str, Any]]:
    log.info("Cookies missing or expired. Log in in the opened browser window.")
    with LinkedInClient(config=cfg) as client:
        return client.login_and_get_cookies()


def fetch_and_store_posts(
    *,
    storage: Any,
    account_id: str,
    cookies: list[dict[str, Any]],
    cfg: LinkedInClientConfig,
    limit: int,
) -> None:
    from storage import compute_source_key  # type: ignore[import-not-found]

    accounts = storage.linkedin_accounts
    posts_repo = storage.feed_posts

    log.info("Fetching posts: limit=%s", limit)
    with LinkedInClient(cookies=cookies, config=cfg) as client:
        posts = client.fetch_posts(limit=limit)
        fresh_cookies = client.get_cookies()
        accounts.update_cookies(account_id=account_id, cookies_json=fresh_cookies)

    run_at = make_run_timestamp()
    payload = [post_to_dict(post) for post in posts]
    upserted = posts_repo.upsert_posts(linkedin_account_id=account_id, posts=payload)
    log.info("Upserted %s posts to Supabase (account=%s)", upserted, account_id)
    try:
        write_run_snapshot(POSTS_PATH, run_at=run_at, posts=payload)
        log.info("Wrote %s (%s posts)", POSTS_PATH, len(payload))
    except Exception as e:
        log.warning("Failed to write %s: %s", POSTS_PATH, e)

    analyzer_input = [to_analyzer_row(p) for p in payload]
    try:
        from post_analyzer.config import load_llm_manager_settings_from_env  # type: ignore[import-not-found]
        from post_analyzer.config import LLMProviderSettings  # type: ignore[import-not-found]
        from post_analyzer.llm_manager import LLMProviderManager  # type: ignore[import-not-found]

        settings = load_llm_manager_settings_from_env()
        mgr = LLMProviderManager(settings=settings)
        desc = mgr.describe()

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
    except Exception:
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
    selection_succeeded = True
    try:
        selected = selector.select(analyzer_input)
    except Exception as e:
        selection_succeeded = False
        selected = []
        log.warning("Selector failed; continuing without selected posts snapshot: %s", e)
    log.info("Selected %s relevant posts via LLM", len(selected))

    for post in selected:
        if not isinstance(post, dict):
            continue
        posts_repo.update_analysis(
            linkedin_account_id=account_id,
            source_key=compute_source_key(post),
            is_relevant=True,
            comment_text=(
                post.get("comment") if isinstance(post.get("comment"), str) else None
            ),
            analysis_error=(
                post.get("comment_error")
                if isinstance(post.get("comment_error"), str)
                else None
            ),
            analysis_payload=(
                post.get("relevance_analysis")
                if isinstance(post.get("relevance_analysis"), dict)
                else None
            ),
        )

    # Mark posts from this fetch that were not selected as irrelevant (same source_key as upsert).
    if selection_succeeded:
        selected_keys = {
            compute_source_key(post)
            for post in selected
            if isinstance(post, dict)
        }
        for post in payload:
            source_key = compute_source_key(post)
            if source_key in selected_keys:
                continue
            posts_repo.update_analysis(
                linkedin_account_id=account_id,
                source_key=source_key,
                is_relevant=False,
                comment_text=None,
                analysis_error=None,
                analysis_payload=None,
            )

    try:
        write_run_snapshot(SELECTED_POSTS_PATH, run_at=run_at, posts=selected)
        log.info("Wrote %s (%s posts)", SELECTED_POSTS_PATH, len(selected))
    except Exception as e:
        log.warning("Failed to write %s: %s", SELECTED_POSTS_PATH, e)


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
    log_supabase_target()

    from storage import PulseStorage  # type: ignore[import-not-found]

    # STORAGE_USER_ID = auth.users.id; service role links rows to that user.
    user_id = os.environ["STORAGE_USER_ID"]
    account_label = os.getenv("STORAGE_ACCOUNT_LABEL")

    storage = PulseStorage()
    accounts = storage.linkedin_accounts
    rows = accounts.list_by_user(user_id=user_id)
    if account_label:
        chosen = next((a for a in rows if a.get("label") == account_label), None)
        if chosen is None and rows:
            log.info(
                "No linkedin_account with label=%r among %s account(s); creating a new one.",
                account_label,
                len(rows),
            )
    else:
        chosen = rows[0] if rows else None

    account_id: str
    cookies: list[dict[str, Any]]
    if chosen is None:
        cookies = login_and_get_cookies(cfg)
        created = accounts.create(
            user_id=user_id, cookies_json=cookies, label=account_label
        )
        account_id = created["id"]
        log.info(
            "Created Supabase linkedin_account=%s for user=%s", account_id, user_id
        )
    else:
        account_id = chosen["id"]
        cookies_val = chosen.get("cookies_json")
        cookies = cookies_val if isinstance(cookies_val, list) else []
        log.info("Loaded cookies from Supabase linkedin_account=%s", account_id)
        if not cookies:
            cookies = login_and_get_cookies(cfg)
            accounts.update_cookies(account_id=account_id, cookies_json=cookies)
            log.info("Supabase cookies were missing; re-logged in and refreshed them.")

    try:
        fetch_and_store_posts(
            storage=storage,
            account_id=account_id,
            cookies=cookies,
            cfg=cfg,
            limit=args.limit,
        )
    except LoginRequiredError:
        log.info("Stored cookies are expired. Re-login and retry once.")
        fresh = login_and_get_cookies(cfg)
        fetch_and_store_posts(
            storage=storage,
            account_id=account_id,
            cookies=fresh,
            cfg=cfg,
            limit=args.limit,
        )
    except Exception:
        log.exception("LinkedInClient demo failed")
        raise


if __name__ == "__main__":
    main()
