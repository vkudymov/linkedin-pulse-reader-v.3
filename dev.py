#!/usr/bin/env python3
"""
Локальная разработка: frontend и worker API в разных терминалах.

    python dev.py api      # worker API
    python dev.py web      # Next.js

Остановка: Ctrl+C в каждом терминале.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"
WORKER_DIR = REPO_ROOT / "worker"
API_APP_DIR = WORKER_DIR / "api" / "src"

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000


def _uvicorn_argv() -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "pulse_api.main:app",
        "--app-dir",
        str(API_APP_DIR),
        "--reload",
        "--host",
        DEFAULT_API_HOST,
        "--port",
        str(DEFAULT_API_PORT),
    ]


def run_api() -> int:
    if not API_APP_DIR.is_dir():
        print(f"ERROR: не найден worker API: {API_APP_DIR}", file=sys.stderr)
        return 1
    print(
        f"Worker API → http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}  (Ctrl+C — остановить)",
        flush=True,
    )
    return int(subprocess.call(_uvicorn_argv(), cwd=WORKER_DIR))


def run_web() -> int:
    npm = shutil.which("npm")
    if npm is None:
        print("ERROR: npm не найден в PATH. Установите Node.js.", file=sys.stderr)
        return 1
    if not (FRONTEND_DIR / "package.json").is_file():
        print(f"ERROR: не найден frontend: {FRONTEND_DIR}", file=sys.stderr)
        return 1
    print(
        "Frontend → npm run dev (обычно http://localhost:3000)  (Ctrl+C — остановить)",
        flush=True,
    )
    return int(subprocess.call([npm, "run", "dev"], cwd=FRONTEND_DIR))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Запуск frontend или worker API (отдельный терминал на сервис).",
    )
    parser.add_argument(
        "command",
        choices=("api", "web"),
        help=f"api — Uvicorn :{DEFAULT_API_PORT}; web — npm run dev",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "api":
        return run_api()
    if args.command == "web":
        return run_web()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
