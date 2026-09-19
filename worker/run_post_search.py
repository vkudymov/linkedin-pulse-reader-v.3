#!/usr/bin/env python3
"""Минимальный запуск LinkedInClient из корня проекта."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LINKEDIN_SRC = ROOT / "LinkedInClient" / "src"
POST_ANALYZER_SRC = ROOT / "PostAnalyzer" / "src"
STORAGE_SRC = ROOT / "Storage" / "src"
JOB_SEARCH_SRC = ROOT / "JobSearch" / "src"
SESSION_SNAPSHOT_SRC = ROOT / "session_snapshot" / "src"
POSTS_PATH = ROOT / "posts.json"
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
if str(JOB_SEARCH_SRC) not in sys.path:
    sys.path.insert(0, str(JOB_SEARCH_SRC))
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
from post_analyzer.config import (  # type: ignore[import-not-found]  # noqa: E402
    LLMProviderSettings,
    load_llm_manager_settings_from_env,
)
from post_analyzer.llm_manager import LLMProviderManager  # type: ignore[import-not-found]  # noqa: E402


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


def create_llm_manager() -> Any:
    mgr = LLMProviderManager(settings=load_llm_manager_settings_from_env())
    desc = mgr.describe()
    if desc.get("provider") != "fake" or desc.get("mode") != "fake":
        return mgr

    mgr.switch(
        primary=LLMProviderSettings(
            provider="openai",
            mode="real",
            model=(
                os.getenv("POST_ANALYZER_LLM_MODEL")
                or os.getenv("POST_ANALYZER_OPENAI_MODEL")
                or os.getenv("OPENAI_MODEL")
                or "deepseek-coder-v2-lite-instruct"
            ),
            base_url=(
                os.getenv("POST_ANALYZER_OPENAI_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or "http://127.0.0.1:1234/v1"
            ),
        ),
        fallback=None,
    )
    return mgr


def ensure_llm_connected() -> None:
    """Pre-flight: проверить, что LLM доступна и отвечает.

    Вызывается до поиска постов. При ошибке worker останавливается,
    без fetch/upsert, чтобы не трогать уже выбранные посты.
    """

    try:
        mgr = create_llm_manager()
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


def _required_env(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise SystemExit(f"Missing required env var: {name}")
    return v


def default_search_prompt_template() -> str:
    prompt_path = ROOT / "PostAnalyzer" / "prompts" / "linkedin_post_relevance.prompt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return (
        "Return ONLY valid JSON with keys match, score, reason, "
        "matched_requirements, missing_requirements, red_flags.\n\n"
        "Post text:\n<<<POST_TEXT>>>"
    )


def default_post_analyzer_config(
    *,
    search_prompt: str | None = None,
    comment_prompt: str | None = None,
) -> PostAnalyzerConfig:
    comment_prompt_path = (
        ROOT / "PostAnalyzer" / "prompts" / "linkedin_comment_generation.prompt"
    )
    template = (search_prompt or "").strip() or default_search_prompt_template()
    return PostAnalyzerConfig(
        relevance_system_prompt=(
            "You are a strict JSON generator. Return ONLY valid JSON (no markdown, no commentary)."
        ),
        relevance_user_prompt="unused: {post_url} {text}",
        comment_system_prompt=None,
        comment_user_prompt="unused: {post_url} {text}",
        comment_prompt_path=None if comment_prompt else str(comment_prompt_path),
        comment_prompt_template=comment_prompt,
        comment_target_language=os.getenv("POST_ANALYZER_COMMENT_LANGUAGE", "ru"),
        search_prompt_template=template,
        search_marker="<<<POST_TEXT>>>",
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
    if account_id is None:
        created = accounts.create(
            user_id=user_id,
            session_snapshot=snapshot,
            label=label,
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
) -> tuple[str, list[dict[str, Any]]]:
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
    return run_at, payload


def _finalize_search_run(
    storage: Any,
    run_id: str | None,
    *,
    status: str,
    fetched_count: int | None = None,
    analyzed_count: int | None = None,
    matched_count: int | None = None,
    error: str | None = None,
) -> None:
    if not run_id:
        return
    try:
        storage.search_runs.finalize(
            run_id=run_id,
            status=status,  # type: ignore[arg-type]
            fetched_count=fetched_count,
            analyzed_count=analyzed_count,
            matched_count=matched_count,
            error=error,
        )
    except Exception as e:
        log.warning("Failed to finalize search_run %s: %s", run_id, e)


def analyze_and_store_posts(
    *,
    storage: Any,
    linkedin_account_id: str,
    post_search_id: str,
    posts: list[dict[str, Any]],
    search_prompt: str,
    comment_prompt: str | None,
) -> tuple[int, int]:
    from storage import compute_source_key  # type: ignore[import-not-found]

    posts_repo = storage.feed_posts
    ids_by_key = posts_repo.list_ids_by_source_keys(
        linkedin_account_id=linkedin_account_id,
        source_keys=[compute_source_key(p) for p in posts if isinstance(p, dict)],
    )

    try:
        mgr = create_llm_manager()
    except Exception:
        log.error(
            "LLM is not configured. Set POST_ANALYZER_LLM_PROVIDER=openai (or ollama) "
            "and ensure LM Studio is running on http://127.0.0.1:1234."
        )
        mgr = None

    analyzer_config = default_post_analyzer_config(search_prompt=search_prompt, comment_prompt=comment_prompt)
    selector = (
        LLMPostSelector(analyzer_config=analyzer_config, llm_manager=mgr)
        if mgr is not None
        else LLMPostSelector(analyzer_config=analyzer_config)
    )

    analyzed_posts = selector.analyze([to_analyzer_row(p) for p in posts if isinstance(p, dict)])
    now = datetime.now(UTC).isoformat()

    upserts: list[dict[str, Any]] = []
    for ap in analyzed_posts:
        if not isinstance(ap, dict):
            continue
        source_key = compute_source_key(ap)
        feed_post_id = ids_by_key.get(source_key)
        if not feed_post_id:
            continue

        rel = ap.get("relevance_analysis") if isinstance(ap.get("relevance_analysis"), dict) else {}
        match = bool(rel.get("match")) if isinstance(rel, dict) else False
        score_raw = rel.get("score") if isinstance(rel, dict) else 0
        score = int(score_raw) if isinstance(score_raw, int) else 0
        score = 0 if score < 0 else 100 if score > 100 else score
        reason = rel.get("reason") if isinstance(rel.get("reason"), str) else ""

        matched = rel.get("matched_requirements")
        missing = rel.get("missing_requirements")
        red_flags = rel.get("red_flags")

        upserts.append(
            {
                "post_search_id": post_search_id,
                "feed_post_id": feed_post_id,
                "match": match,
                "score": score,
                "reason": reason,
                "matched_requirements": matched if isinstance(matched, list) else [],
                "missing_requirements": missing if isinstance(missing, list) else [],
                "red_flags": red_flags if isinstance(red_flags, list) else [],
                "comment_text": ap.get("comment") if isinstance(ap.get("comment"), str) else None,
                "comment_error": ap.get("comment_error") if isinstance(ap.get("comment_error"), str) else None,
                "raw_payload": rel if isinstance(rel, dict) else None,
                "error": ap.get("analysis_error") if isinstance(ap.get("analysis_error"), str) else None,
                "analyzed_at": now,
                "updated_at": now,
            }
        )

    written = storage.post_analyses.upsert_analyses(analyses=upserts)
    matched = sum(1 for u in upserts if u.get("match"))
    log.info("Wrote %s post_analyses row(s) (post_search=%s)", written, post_search_id)
    return written, matched


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch LinkedIn posts via LinkedInClient.")
    parser.add_argument("--post-search-id", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--account-label", default=None)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    log.info(
        "Starting LinkedIn post search: post_search_id=%s limit=%s headless=%s",
        args.post_search_id,
        args.limit,
        args.headless,
    )
    login_timeout_ms = int(os.getenv("LINKEDIN_AUTH_TIMEOUT_MS", "300000"))
    cfg = LinkedInClientConfig(
        browser=BrowserConfig(headless=args.headless, timeout_ms=login_timeout_ms)
    )
    log_supabase_target()

    ensure_llm_connected()

    from storage import PulseStorage, pick_linkedin_account_row  # type: ignore[import-not-found]

    # STORAGE_USER_ID = auth.users.id; service role links rows to that user.
    user_id = _required_env("STORAGE_USER_ID")
    post_search_id = str(args.post_search_id)
    search_run_id = (os.getenv("SEARCH_RUN_ID") or "").strip() or None
    storage = PulseStorage()

    ps_row = storage.post_searches.get_by_id(post_search_id=post_search_id)
    if not ps_row or ps_row.get("user_id") != user_id:
        raise SystemExit("ERROR: post_search not found")
    if ps_row.get("status") == "paused":
        log.info("Post search is paused; skipping.")
        return

    search_prompt = str(ps_row.get("search_prompt") or "").strip()
    comment_prompt = ps_row.get("comment_prompt") if isinstance(ps_row.get("comment_prompt"), str) else None
    comment_prompt = comment_prompt.strip() if comment_prompt and comment_prompt.strip() else None
    if not search_prompt:
        raise SystemExit("ERROR: search_prompt is empty")

    account_label = (
        str(args.account_label)
        if args.account_label
        else (
            ps_row.get("account_label")
            if isinstance(ps_row.get("account_label"), str) and ps_row.get("account_label")
            else os.getenv("STORAGE_ACCOUNT_LABEL")
        )
    )

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
        run_at, payload = fetch_and_store_posts(
            storage=storage,
            account_id=account_id,
            snapshot=snapshot,
            cfg=cfg,
            limit=args.limit,
        )
        analyzed, matched = analyze_and_store_posts(
            storage=storage,
            linkedin_account_id=account_id,
            post_search_id=post_search_id,
            posts=payload,
            search_prompt=search_prompt,
            comment_prompt=comment_prompt,
        )
        storage.post_searches.update(post_search_id=post_search_id, last_run_at=run_at)
        _finalize_search_run(
            storage,
            search_run_id,
            status="done",
            fetched_count=len(payload),
            analyzed_count=analyzed,
            matched_count=matched,
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
        run_at, payload = fetch_and_store_posts(
            storage=storage,
            account_id=account_id,
            snapshot=snapshot,
            cfg=cfg,
            limit=args.limit,
        )
        analyzed, matched = analyze_and_store_posts(
            storage=storage,
            linkedin_account_id=account_id,
            post_search_id=post_search_id,
            posts=payload,
            search_prompt=search_prompt,
            comment_prompt=comment_prompt,
        )
        storage.post_searches.update(post_search_id=post_search_id, last_run_at=run_at)
        _finalize_search_run(
            storage,
            search_run_id,
            status="done",
            fetched_count=len(payload),
            analyzed_count=analyzed,
            matched_count=matched,
        )
    except FeedLoadError as e:
        log.error("%s", e)
        _finalize_search_run(storage, search_run_id, status="error", error=str(e))
        raise SystemExit(1) from None
    except Exception as e:
        log.exception("LinkedInClient demo failed")
        _finalize_search_run(storage, search_run_id, status="error", error=str(e))
        raise


if __name__ == "__main__":
    main()
