#!/usr/bin/env python3
"""Минимальный запуск LinkedInClient из корня проекта."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LINKEDIN_SRC = ROOT / "LinkedInClient" / "src"
POST_ANALYZER_SRC = ROOT / "PostAnalyzer" / "src"
STORAGE_SRC = ROOT / "Storage" / "src"
SESSION_SNAPSHOT_SRC = ROOT / "session_snapshot" / "src"
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
if str(SESSION_SNAPSHOT_SRC) not in sys.path:
    sys.path.insert(0, str(SESSION_SNAPSHOT_SRC))

from linkedin_client import LinkedInClient, LinkedInClientConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.browser import BrowserConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.exceptions import FeedLoadError, LoginRequiredError  # type: ignore[import-not-found]  # noqa: E402
from session_snapshot import (  # noqa: E402
    SessionLoggedOutError,
    has_auth_cookie,
    load_snapshot,
    should_save_back,
)

from post_analyzer import LLMPostSelector, PostAnalyzerConfig  # type: ignore[import-not-found]  # noqa: E402


class _ColorLevelFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.levelname == "ERROR":
            record.levelname = f"\x1b[31m{record.levelname}\x1b[0m"
        return super().format(record)


_handler = logging.StreamHandler()
_handler.setFormatter(_ColorLevelFormatter("%(levelname)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
log = logging.getLogger(__name__)

LLM_CONNECT_FAILED_EXIT_CODE = 2


def ensure_llm_connected() -> None:
    """Pre-flight: проверить, что LLM доступна и отвечает.

    Вызывается до поиска постов. При ошибке worker останавливается,
    без fetch/upsert, чтобы не трогать уже выбранные посты.
    """

    try:
        from post_analyzer.config import load_llm_manager_settings_from_env  # type: ignore[import-not-found]
        from post_analyzer.config import LLMProviderSettings  # type: ignore[import-not-found]
        from post_analyzer.llm_manager import LLMProviderManager  # type: ignore[import-not-found]

        settings = load_llm_manager_settings_from_env()
        mgr = LLMProviderManager(settings=settings)
        desc = mgr.describe()

        if desc.get("provider") == "fake" and desc.get("mode") == "fake":
            lmstudio_base_url = (
                os.getenv("POST_ANALYZER_OPENAI_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or "http://127.0.0.1:1234/v1"
            )
            lmstudio_model = (
                os.getenv("POST_ANALYZER_LLM_MODEL")
                or os.getenv("POST_ANALYZER_OPENAI_MODEL")
                or os.getenv("OPENAI_MODEL")
                or "deepseek-coder-v2-lite-instruct"
            )
            mgr.switch(
                primary=LLMProviderSettings(
                    provider="openai",
                    mode="real",
                    model=lmstudio_model,
                    base_url=lmstudio_base_url,
                ),
                fallback=None,
            )

        mgr.test_connection()

        desc = mgr.describe()
        log.info(
            "LLM connected: provider=%s model=%s — модель отвечает.",
            desc.get("provider") or "<unknown>",
            desc.get("model") or "<unknown>",
        )
    except SystemExit:
        raise
    except Exception as e:
        log.error("LLM not connected: нет коннекта, модель не работает. %s", e)
        raise SystemExit(LLM_CONNECT_FAILED_EXIT_CODE) from None


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
            'Return strict JSON only. Use schema: {"relevant": true|false, "reason": "short explanation"}.'
        ),
        relevance_user_prompt=(
            "Post URL:\n{post_url}\n\nPost text:\n{text}\n\n"
            'Reply with strict JSON only: {{"relevant": true|false, "reason": "short explanation"}}'
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
                "avatar_url": getattr(author, "avatar_url", None),
            }
        ),
    }


def extract_post_image_urls(media_urls: list[str]) -> list[str]:
    """Pick likely post image URLs from a noisy media_urls list.

    LinkedIn pages often include many avatar/group images; this helper keeps only
    URLs that look like actual post media so we can persist and render them.
    """
    out: list[str] = []
    for url in media_urls:
        if not isinstance(url, str):
            continue
        u = url.strip()
        if not u.startswith("http"):
            continue
        # Heuristic: feedshare/articleshare are typically the post images.
        if "feedshare-" not in u and "articleshare-" not in u:
            continue
        out.append(u)
        if len(out) >= 8:
            break
    # De-dup while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for u in out:
        if u in seen:
            continue
        seen.add(u)
        deduped.append(u)
    return deduped


def store_post_images(
    storage: Any,
    *,
    user_id: str,
    feed_post_id: str,
    urls: list[str],
) -> None:
    """Download + upload post images to Supabase Storage, then persist metadata.

    This is best-effort and must not affect the main post ingest / analysis flow.
    """
    if not urls:
        return

    try:
        from urllib.request import Request, urlopen
    except Exception as e:  # pragma: no cover
        log.warning("Media download unavailable: %s", e)
        return

    ssl_ctx = None
    ssl_ctx_source = "none"
    try:
        import ssl

        try:
            import certifi  # type: ignore[import-not-found]

            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            ssl_ctx_source = "certifi"
        except Exception:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx_source = "default"
    except Exception as e:  # pragma: no cover
        ssl_ctx = None
        ssl_ctx_source = "import_failed"

    bucket = "post_media"
    inserted: list[dict[str, Any]] = []

    for idx, url in enumerate(urls, start=1):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with (
                urlopen(req, timeout=20, context=ssl_ctx)
                if ssl_ctx is not None
                else urlopen(req, timeout=20)
            ) as resp:
                content_type = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip()
                body = resp.read()
        except Exception as e:
            log.warning("Failed to download media url=%s: %s", url, e)
            continue

        if not body:
            continue

        ext = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
        }.get(content_type)
        if ext is None:
            # Fallback: try to guess from URL path
            m = re.search(r"\.(jpg|jpeg|png|webp|gif)(?:\\?|$)", url, re.IGNORECASE)
            ext = (m.group(1).lower().replace("jpeg", "jpg") if m else None)
        if ext is None:
            log.warning("Skipping media with unknown content-type=%r url=%s", content_type, url)
            continue

        object_path = f"{user_id}/{feed_post_id}/{idx}.{ext}"
        try:
            # supabase-py v2 API
            storage.client.storage.from_(bucket).upload(  # type: ignore[attr-defined]
                object_path,
                body,
                # storage3 expects header values to be strings; "upsert" is mapped to "x-upsert"
                file_options={
                    "content-type": content_type or f"image/{ext}",
                    "upsert": "true",
                },
            )
            public_url = storage.client.storage.from_(bucket).get_public_url(object_path)  # type: ignore[attr-defined]
            inserted.append(
                {
                    "feed_post_id": feed_post_id,
                    "original_url": url,
                    "object_path": object_path,
                    "public_url": public_url,
                    "position": idx,
                }
            )
        except Exception as e:
            log.warning("Failed to upload media path=%s: %s", object_path, e)
            continue

    if not inserted:
        return

    try:
        storage.client.table("feed_post_media").upsert(  # type: ignore[attr-defined]
            inserted,
            on_conflict="feed_post_id,position",
        ).execute()
    except Exception as e:
        log.warning("Failed to persist feed_post_media rows: %s", e)


def copy_analysis_fields(
    *,
    payload_post: dict[str, Any],
    analyzed_post: dict[str, Any],
) -> None:
    for field in (
        "result",
        "reason",
        "relevance_analysis",
        "analysis_error",
        "comment",
        "comment_error",
    ):
        if field in analyzed_post:
            payload_post[field] = analyzed_post[field]


def login_and_export_snapshot(cfg: LinkedInClientConfig) -> dict[str, Any]:
    log.info("Cookies missing or expired. Log in in the opened browser window.")
    with LinkedInClient(config=cfg) as client:
        client.login_and_get_cookies()
        if not should_save_back(client.page.url):
            raise LoginRequiredError(
                "LinkedIn login did not reach a logged-in page; cookies were not saved."
            )
        try:
            return client.export_session_snapshot({})
        except SessionLoggedOutError as e:
            raise LoginRequiredError(str(e)) from e


def _persist_snapshot(accounts: Any, *, user_id: str, account_id: str | None, snapshot: dict[str, Any], label: str | None) -> str:
    cookies = snapshot.get("cookies") if isinstance(snapshot, dict) else None
    cookie_list = cookies if isinstance(cookies, list) else []
    if account_id is None:
        created = accounts.create(
            user_id=user_id,
            cookies_json=cookie_list,
            label=label,
            session_snapshot=snapshot,
        )
        return created["id"]
    accounts.update_session(account_id=account_id, session_snapshot=snapshot)
    return account_id


def fetch_and_store_posts(
    *,
    storage: Any,
    account_id: str,
    snapshot: dict[str, Any],
    cfg: LinkedInClientConfig,
    limit: int,
) -> None:
    from storage import compute_source_key  # type: ignore[import-not-found]

    accounts = storage.linkedin_accounts
    posts_repo = storage.feed_posts

    log.info("Fetching posts: limit=%s", limit)
    with LinkedInClient(session_snapshot=snapshot, config=cfg) as client:
        posts = client.fetch_posts(limit=limit)
        if not should_save_back(client.page.url):
            raise LoginRequiredError(
                "LinkedIn returned a login/authwall page; session was not saved back."
            )
        try:
            fresh_snapshot = client.export_session_snapshot(snapshot)
        except SessionLoggedOutError as e:
            raise LoginRequiredError(str(e)) from e
        accounts.update_session(account_id=account_id, session_snapshot=fresh_snapshot)

    run_at = make_run_timestamp()
    payload = [post_to_dict(post) for post in posts]
    for idx, post in enumerate(payload, start=1):
        post["result"] = "не проверено"
        post["reason"] = None
        log.info(
            "Post %s/%s: state=read source_key=%s",
            idx,
            limit,
            compute_source_key(post),
        )
    upserted = posts_repo.upsert_posts(linkedin_account_id=account_id, posts=payload)
    log.info("Upserted %s posts to Supabase (account=%s)", upserted, account_id)

    # Best-effort: persist post images into Supabase Storage for UI rendering.
    try:
        source_keys = [compute_source_key(post) for post in payload]
        ids_by_key = posts_repo.list_ids_by_source_keys(
            linkedin_account_id=account_id,
            source_keys=source_keys,
        )
        user_id = os.environ.get("STORAGE_USER_ID", "")
        if user_id:
            for post in payload:
                sk = compute_source_key(post)
                feed_post_id = ids_by_key.get(sk)
                if not feed_post_id:
                    continue
                media_urls_val = post.get("media_urls")
                media_urls = (
                    [u for u in media_urls_val if isinstance(u, str)]
                    if isinstance(media_urls_val, list)
                    else []
                )
                urls = extract_post_image_urls(media_urls)
                store_post_images(storage, user_id=user_id, feed_post_id=feed_post_id, urls=urls)
    except Exception as e:
        log.warning("Post media persistence failed (ignored): %s", e)
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
            lmstudio_base_url = (
                os.getenv("POST_ANALYZER_OPENAI_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or "http://127.0.0.1:1234/v1"
            )
            lmstudio_model = (
                os.getenv("POST_ANALYZER_LLM_MODEL")
                or os.getenv("POST_ANALYZER_OPENAI_MODEL")
                or os.getenv("OPENAI_MODEL")
                or "deepseek-coder-v2-lite-instruct"
            )
            mgr.switch(
                primary=LLMProviderSettings(
                    provider="openai",
                    mode="real",
                    model=lmstudio_model,
                    base_url=lmstudio_base_url,
                ),
                fallback=None,
            )
    except Exception:
        log.error(
            "LLM is not configured. Set POST_ANALYZER_LLM_PROVIDER=openai (or ollama) "
            "and ensure LM Studio is running on http://127.0.0.1:1234."
        )
        mgr = None

    selector = (
        LLMPostSelector(analyzer_config=default_post_analyzer_config(), llm_manager=mgr)
        if mgr is not None
        else LLMPostSelector(analyzer_config=default_post_analyzer_config())
    )
    selection_succeeded = True
    analyzed_by_key: dict[str, dict[str, Any]] = {}
    try:
        analyzed_posts = selector.analyze(analyzer_input)
        analyzed_by_key = {
            compute_source_key(post): post
            for post in analyzed_posts
            if isinstance(post, dict)
        }
        for post in payload:
            analyzed_post = analyzed_by_key.get(compute_source_key(post))
            if analyzed_post is not None:
                copy_analysis_fields(payload_post=post, analyzed_post=analyzed_post)
        selected = [
            post
            for post in analyzed_posts
            if isinstance(post, dict) and post.get("result") == "принято"
        ]
    except Exception as e:
        selection_succeeded = False
        selected = []
        reason = f"Selector failed: {e}"
        for post in payload:
            post["result"] = "ошибка анализа"
            post["reason"] = reason
            post["analysis_error"] = reason
        log.warning(
            "Selector failed; continuing without selected posts snapshot: %s", e
        )
    log.info("Selected %s relevant posts via LLM", len(selected))

    post_numbers_by_key = {
        compute_source_key(post): idx for idx, post in enumerate(payload, start=1)
    }
    selected_by_key: dict[str, dict[str, Any]] = {}
    for post in selected:
        if not isinstance(post, dict):
            continue
        source_key = compute_source_key(post)
        selected_by_key[source_key] = post
        post_number = post_numbers_by_key.get(source_key, "?")
        log.info(
            "Post %s/%s: state=analyze result=принято source_key=%s",
            post_number,
            limit,
            source_key,
        )
        posts_repo.update_analysis(
            linkedin_account_id=account_id,
            source_key=source_key,
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
        for post in payload:
            source_key = compute_source_key(post)
            if source_key in selected_by_key:
                continue
            post_number = post_numbers_by_key.get(source_key, "?")
            log.info(
                "Post %s/%s: state=analyze result=отклонено source_key=%s",
                post_number,
                limit,
                source_key,
            )
            posts_repo.update_analysis(
                linkedin_account_id=account_id,
                source_key=source_key,
                is_relevant=False,
                comment_text=None,
                analysis_error=(
                    analyzed_by_key[source_key].get("analysis_error")
                    if isinstance(analyzed_by_key.get(source_key), dict)
                    and isinstance(
                        analyzed_by_key[source_key].get("analysis_error"), str
                    )
                    else None
                ),
                analysis_payload=(
                    analyzed_by_key[source_key].get("relevance_analysis")
                    if isinstance(analyzed_by_key.get(source_key), dict)
                    and isinstance(
                        analyzed_by_key[source_key].get("relevance_analysis"), dict
                    )
                    else None
                ),
            )

    try:
        write_run_snapshot(POSTS_PATH, run_at=run_at, posts=payload)
        log.info("Updated %s with analysis results", POSTS_PATH)
    except Exception as e:
        log.warning("Failed to update %s with analysis results: %s", POSTS_PATH, e)

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
    login_timeout_ms = int(os.getenv("LINKEDIN_AUTH_TIMEOUT_MS", "300000"))
    cfg = LinkedInClientConfig(
        browser=BrowserConfig(headless=args.headless, timeout_ms=login_timeout_ms)
    )
    log_supabase_target()

    ensure_llm_connected()

    from storage import PulseStorage, pick_linkedin_account_row  # type: ignore[import-not-found]

    # STORAGE_USER_ID = auth.users.id; service role links rows to that user.
    user_id = os.environ["STORAGE_USER_ID"]
    account_label = os.getenv("STORAGE_ACCOUNT_LABEL")

    storage = PulseStorage()
    accounts = storage.linkedin_accounts
    rows = accounts.list_by_user(user_id=user_id)
    chosen = pick_linkedin_account_row(
        rows,
        label=account_label,
        create_new_on_label_miss=True,
    )
    if account_label and chosen is None and rows:
        log.info(
            "No linkedin_account with label=%r among %s account(s); creating a new one.",
            account_label,
            len(rows),
        )

    account_id: str
    snapshot: dict[str, Any]
    if chosen is None:
        snapshot = login_and_export_snapshot(cfg)
        account_id = _persist_snapshot(
            accounts, user_id=user_id, account_id=None, snapshot=snapshot, label=account_label
        )
        log.info(
            "Created Supabase linkedin_account=%s for user=%s", account_id, user_id
        )
    else:
        account_id = chosen["id"]
        snapshot = load_snapshot(chosen)
        cookies = snapshot.get("cookies") if isinstance(snapshot.get("cookies"), list) else []
        log.info(
            "Loaded session from Supabase linkedin_account=%s (cookies=%s, li_at=%s)",
            account_id,
            len(cookies),
            "yes" if has_auth_cookie(cookies) else "no",
        )
        if not has_auth_cookie(cookies):
            snapshot = login_and_export_snapshot(cfg)
            _persist_snapshot(
                accounts,
                user_id=user_id,
                account_id=account_id,
                snapshot=snapshot,
                label=account_label,
            )
            log.info("Supabase session was missing; re-logged in and refreshed it.")

    try:
        fetch_and_store_posts(
            storage=storage,
            account_id=account_id,
            snapshot=snapshot,
            cfg=cfg,
            limit=args.limit,
        )
    except LoginRequiredError:
        log.info("Stored session is expired. Re-login and retry once.")
        snapshot = login_and_export_snapshot(cfg)
        _persist_snapshot(
            accounts,
            user_id=user_id,
            account_id=account_id,
            snapshot=snapshot,
            label=account_label,
        )
        fetch_and_store_posts(
            storage=storage,
            account_id=account_id,
            snapshot=snapshot,
            cfg=cfg,
            limit=args.limit,
        )
    except FeedLoadError as e:
        log.error("%s", e)
        raise SystemExit(1) from None
    except Exception:
        log.exception("LinkedInClient demo failed")
        raise


if __name__ == "__main__":
    main()
