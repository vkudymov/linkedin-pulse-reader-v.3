from __future__ import annotations

import argparse
import sys
from contextlib import suppress
from pathlib import Path

# EN: Repo-local runner. We add ./src to sys.path so this script can be Run/Debugged
#     directly from Cursor without requiring `pip install -e .`.
# RU: Локальный runner для репозитория. Добавляем ./src в sys.path, чтобы файл можно было
#     запускать/дебажить напрямую из Cursor без `pip install -e .`.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from linkedin_client import LinkedInClient, LinkedInClientConfig
from linkedin_client.browser import BrowserConfig
from linkedin_client.exceptions import LoginRequiredError


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
    trace_path: Path | None,
) -> list[dict[str, Any]]:
    # EN: Manual authentication flow. User enters login/password in the opened Chromium window.
    #     When LinkedIn redirects to /feed, we extract cookies and return them to the caller.
    # RU: Ручная авторизация. Пользователь вводит логин/пароль в открытом окне Chromium.
    #     Когда LinkedIn редиректит на /feed — извлекаем cookies и возвращаем вызывающему коду.
    print("Authentication required. Please log in in the opened browser window...")
    with LinkedInClient(cookies=None, config=cfg) as client:
        _maybe_start_trace(client, trace_path)
        try:
            refreshed = client.login_and_get_cookies()
            # cookies.json persistence is handled by ../../run_post_search.py.
            print(f"Received {len(refreshed)} cookies.")
            return refreshed
        finally:
            _maybe_stop_trace(client, trace_path)


def main() -> int:
    artifacts_dir_default = REPO_ROOT / "run" / "artifacts"

    ap = argparse.ArgumentParser(
        description="Local runner for LinkedInClient (Cursor Run/Debug friendly)."
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=30,
        help="How many posts to fetch (used by fetch-posts and default run).",
    )
    ap.add_argument(
        "--headless", action="store_true", help="Run Chromium in headless mode."
    )
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

    cookies = None

    cfg = LinkedInClientConfig(
        browser=BrowserConfig(headless=args.headless, timeout_ms=args.timeout_ms)
    )

    cmd = args.cmd or "fetch-posts"

    if cmd == "login":
        # EN: Interactive login only; does not fetch posts.
        # RU: Только интерактивный логин; посты не загружает.
        with LinkedInClient(cookies=None, config=cfg) as client:
            _maybe_start_trace(client, args.trace)
            try:
                refreshed = client.login_and_get_cookies()
                # cookies.json persistence is handled by ../../run_post_search.py.
                print(f"Received {len(refreshed)} cookies.")
            finally:
                _maybe_stop_trace(client, args.trace)

        return 0

    if cmd == "status":
        # EN: Quick check: opens a page and prints whether we're on feed (best-effort).
        # RU: Быстрая проверка: открывает страницу и печатает, на фиде ли мы (best-effort).
        with LinkedInClient(cookies=cookies, config=cfg) as client:
            print("logged_in:", client.is_logged_in())
        return 0

    if cmd == "fetch-posts":
        # EN: Main flow:
        #     - Use cookies if present
        #     - If missing or expired → interactive login → persist cookies → fetch posts
        # RU: Основной сценарий:
        #     - Используем cookies если они есть
        #     - Если нет или протухли → ручной логин → сохраняем cookies → забираем посты
        #
        # EN: If cookies are missing, do an interactive login first.
        # RU: Если cookies отсутствуют — сначала делаем интерактивный логин.
        if not cookies:
            cookies = _manual_login_and_save_cookies(
                cfg=cfg, trace_path=args.trace
            )

        try:
            with LinkedInClient(cookies=cookies, config=cfg) as client:
                _maybe_start_trace(client, args.trace)
                try:
                    posts = client.fetch_posts(limit=args.limit)
                    print(f"Fetched {len(posts)} posts.")
                    # posts.json/cookies.json persistence is handled by ../../run_post_search.py.
                except Exception:
                    if args.screenshot_on_error:
                        artifacts_dir_default.mkdir(parents=True, exist_ok=True)
                        path = artifacts_dir_default / "error.png"
                        with suppress(Exception):
                            client.page.screenshot(path=str(path), full_page=True)
                            print(f"Saved screenshot to {path}.")
                    raise
                finally:
                    _maybe_stop_trace(client, args.trace)
            return 0
        except LoginRequiredError:
            # EN: Cookies were provided but are not valid anymore. Re-login and retry once.
            # RU: Cookies были, но стали невалидными. Делаем логин и повторяем один раз.
            cookies = _manual_login_and_save_cookies(
                cfg=cfg, trace_path=args.trace
            )
            with LinkedInClient(cookies=cookies, config=cfg) as client:
                posts = client.fetch_posts(limit=args.limit)
                print(f"Fetched {len(posts)} posts.")
                # posts.json/cookies.json persistence is handled by ../../run_post_search.py.
            return 0

    raise SystemExit(f"Unknown command: {cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
