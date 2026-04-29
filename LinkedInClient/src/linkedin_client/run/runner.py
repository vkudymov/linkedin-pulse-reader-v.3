from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from linkedin_client import LinkedInClient, LinkedInClientConfig
from linkedin_client.browser import BrowserConfig
from linkedin_client.exceptions import LoginRequiredError


def _load_cookies(path: Path) -> list[dict[str, Any]] | None:
    # EN: Cookies are stored as Playwright's JSON list (array of cookie objects).
    # RU: Cookies хранятся в формате Playwright (JSON-массив объектов cookies).
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError(f"Expected JSON array of cookies in {path}")
    return raw


def _save_cookies(path: Path, cookies: list[dict[str, Any]]) -> None:
    # EN: Never commit real cookies. Prefer keeping them in ./run/ and gitignored.
    # RU: Никогда не коммитьте реальные cookies. Держите их в ./run/ и добавьте в gitignore.
    path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_posts(path: Path, posts: list[Any]) -> None:
    # EN: Post is a dataclass; store a JSON-friendly view for quick inspection.
    # RU: Post — dataclass; сохраняем JSON-представление для быстрой проверки результатов.
    payload: list[dict[str, Any]] = []
    for p in posts:
        author = getattr(p, "author", None)
        payload.append(
            {
                "urn": getattr(p, "urn", None),
                "post_url": getattr(p, "post_url", None),
                "published_at_text": getattr(p, "published_at_text", None),
                "content": getattr(p, "content", None),
                "reactions_count": getattr(p, "reactions_count", None),
                "comments_count": getattr(p, "comments_count", None),
                "media_urls": list(getattr(p, "media_urls", []) or []),
                "author": None
                if author is None
                else {
                    "name": getattr(author, "name", None),
                    "headline": getattr(author, "headline", None),
                    "profile_url": getattr(author, "profile_url", None),
                    "urn": getattr(author, "urn", None),
                },
            }
        )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _maybe_start_trace(client: LinkedInClient, trace_path: Path | None) -> None:
    # EN: Optional Playwright trace to debug flaky feed loading / selector changes.
    # RU: Опциональный trace Playwright для отладки флейков/изменений DOM/селекторов.
    if trace_path is None:
        return
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    client.page.context.tracing.start(screenshots=True, snapshots=True, sources=True)


def _maybe_stop_trace(client: LinkedInClient, trace_path: Path | None) -> None:
    if trace_path is None:
        return
    client.page.context.tracing.stop(path=str(trace_path))


def _manual_login_and_save_cookies(
    *,
    cfg: LinkedInClientConfig,
    cookies_path: Path,
    trace_path: Path | None,
) -> list[dict[str, Any]]:
    # EN: Manual authentication flow. User enters login/password in the opened Chromium window.
    #     When LinkedIn redirects to /feed, we extract cookies and persist them to ./run/cookies.json.
    # RU: Ручная авторизация. Пользователь вводит логин/пароль в открытом окне Chromium.
    #     Когда LinkedIn редиректит на /feed — извлекаем cookies и сохраняем в ./run/cookies.json.
    print("Authentication required. Please log in in the opened browser window...")
    with LinkedInClient(cookies=None, config=cfg) as client:
        _maybe_start_trace(client, trace_path)
        try:
            refreshed = client.login_and_get_cookies()
            cookies_path.parent.mkdir(parents=True, exist_ok=True)
            _save_cookies(cookies_path, refreshed)
            print(f"Saved {len(refreshed)} cookies to {cookies_path}.")
            return refreshed
        finally:
            _maybe_stop_trace(client, trace_path)


def main() -> int:
    # EN: This runner writes files to ./run/ under current working directory.
    # RU: Этот runner пишет файлы в ./run/ относительно текущей директории запуска.
    cwd = Path.cwd()
    cookies_path_default = cwd / "run" / "cookies.json"
    posts_path_default = cwd / "run" / "posts.json"
    artifacts_dir_default = cwd / "run" / "artifacts"

    ap = argparse.ArgumentParser(
        description="Local runner for LinkedInClient (packaged: python -m linkedin_client.run)."
    )
    ap.add_argument(
        "--cookies",
        type=Path,
        default=cookies_path_default,
        help="Path to cookies JSON (Playwright cookie list).",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=10,
        help="How many posts to fetch (used by fetch-posts and default run).",
    )
    ap.add_argument(
        "--posts-out",
        type=Path,
        default=posts_path_default,
        help="Where to save fetched posts JSON.",
    )
    ap.add_argument("--headless", action="store_true", help="Run Chromium in headless mode.")
    ap.add_argument(
        "--timeout-ms",
        type=int,
        default=60_000,
        help="Default Playwright timeout for waits/navigation.",
    )
    ap.add_argument(
        "--trace",
        type=Path,
        default=None,
        help="Save Playwright trace to this path (e.g. run/artifacts/trace.zip).",
    )
    ap.add_argument(
        "--screenshot-on-error",
        action="store_true",
        help="Save screenshot to run/artifacts/ on failure.",
    )

    sub = ap.add_subparsers(dest="cmd", required=False)

    p_login = sub.add_parser("login", help="Open login page and save cookies.")
    p_login.add_argument(
        "--force",
        action="store_true",
        help="Overwrite cookies file even if it already exists.",
    )

    sub.add_parser("fetch-posts", help="Fetch posts from LinkedIn feed.")
    sub.add_parser("status", help="Print whether the client appears logged-in.")

    args = ap.parse_args()

    cookies_path: Path = args.cookies
    cookies = _load_cookies(cookies_path)

    cfg = LinkedInClientConfig(
        browser=BrowserConfig(headless=args.headless, timeout_ms=args.timeout_ms)
    )

    cmd = args.cmd or "fetch-posts"

    if cmd == "login":
        # EN: Interactive login only; does not fetch posts.
        # RU: Только интерактивный логин; посты не загружает.
        if cookies_path.exists() and not args.force:
            raise SystemExit(
                f"{cookies_path} already exists. Use 'login --force' to overwrite."
            )

        with LinkedInClient(cookies=None, config=cfg) as client:
            _maybe_start_trace(client, args.trace)
            try:
                refreshed = client.login_and_get_cookies()
                cookies_path.parent.mkdir(parents=True, exist_ok=True)
                _save_cookies(cookies_path, refreshed)
                print(f"Saved {len(refreshed)} cookies to {cookies_path}.")
            finally:
                _maybe_stop_trace(client, args.trace)

        return 0

    if cmd == "status":
        # EN: Quick check: opens a page and prints whether we're on feed (best-effort).
        # RU: Быстрая проверка: открывает страницу и печатает, на фиде ли мы (best-effort).
        with LinkedInClient(cookies=cookies, config=cfg) as client:
            print("logged_in:", client.is_logged_in())
            refreshed = client.get_cookies()
            cookies_path.parent.mkdir(parents=True, exist_ok=True)
            _save_cookies(cookies_path, refreshed)
        return 0

    if cmd == "fetch-posts":
        # EN: Main flow:
        #     - Use cookies if present
        #     - If missing or expired → interactive login → persist cookies → fetch posts
        # RU: Основной сценарий:
        #     - Используем cookies если они есть
        #     - Если нет или протухли → ручной логин → сохраняем cookies → забираем посты
        if not cookies:
            cookies = _manual_login_and_save_cookies(
                cfg=cfg, cookies_path=cookies_path, trace_path=args.trace
            )

        try:
            with LinkedInClient(cookies=cookies, config=cfg) as client:
                _maybe_start_trace(client, args.trace)
                try:
                    posts = client.fetch_posts(limit=args.limit)
                    print(f"Fetched {len(posts)} posts.")
                    args.posts_out.parent.mkdir(parents=True, exist_ok=True)
                    _save_posts(args.posts_out, posts)
                    print(f"Saved posts JSON to {args.posts_out}.")

                    refreshed = client.get_cookies()
                    cookies_path.parent.mkdir(parents=True, exist_ok=True)
                    _save_cookies(cookies_path, refreshed)
                    print(f"Saved {len(refreshed)} cookies to {cookies_path}.")
                except Exception:
                    if args.screenshot_on_error:
                        artifacts_dir_default.mkdir(parents=True, exist_ok=True)
                        path = artifacts_dir_default / "error.png"
                        try:
                            client.page.screenshot(path=str(path), full_page=True)
                            print(f"Saved screenshot to {path}.")
                        except Exception:
                            pass
                    raise
                finally:
                    _maybe_stop_trace(client, args.trace)
            return 0
        except LoginRequiredError:
            # EN: Cookies were provided but are not valid anymore. Re-login and retry once.
            # RU: Cookies были, но стали невалидными. Делаем логин и повторяем один раз.
            cookies = _manual_login_and_save_cookies(
                cfg=cfg, cookies_path=cookies_path, trace_path=args.trace
            )
            with LinkedInClient(cookies=cookies, config=cfg) as client:
                posts = client.fetch_posts(limit=args.limit)
                print(f"Fetched {len(posts)} posts.")
                args.posts_out.parent.mkdir(parents=True, exist_ok=True)
                _save_posts(args.posts_out, posts)
                print(f"Saved posts JSON to {args.posts_out}.")

                refreshed = client.get_cookies()
                cookies_path.parent.mkdir(parents=True, exist_ok=True)
                _save_cookies(cookies_path, refreshed)
                print(f"Saved {len(refreshed)} cookies to {cookies_path}.")
            return 0

    raise SystemExit(f"Unknown command: {cmd}")

