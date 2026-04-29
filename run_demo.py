#!/usr/bin/env python3
"""Минимальный запуск LinkedInClient из корня проекта."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LINKEDIN_SRC = ROOT / "LinkedInClient" / "src"
COOKIES_PATH = ROOT / "cookies.json"
POSTS_PATH = ROOT / "posts.json"

if str(LINKEDIN_SRC) not in sys.path:
    sys.path.insert(0, str(LINKEDIN_SRC))

from linkedin_client import LinkedInClient, LinkedInClientConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.browser import BrowserConfig  # type: ignore[import-not-found]  # noqa: E402
from linkedin_client.exceptions import LoginRequiredError  # type: ignore[import-not-found]  # noqa: E402

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

    save_json(POSTS_PATH, [post_to_dict(post) for post in posts])
    log.info("Saved %s posts to %s", len(posts), POSTS_PATH)
    log.info("Updated cookies in %s", COOKIES_PATH)


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
