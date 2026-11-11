from __future__ import annotations

import os
import sys
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from ..search_runs.client_message import client_failure_message

RunStatus = Literal["running", "done", "error"]
LLM_CONNECT_FAILED_EXIT_CODE = 2


@dataclass(slots=True)
class PostSearchSession:
    session_id: str
    user_id: str
    post_search_id: str
    search_run_id: str | None
    status: RunStatus
    message: str | None
    future: Future[None] | None = None


class PostSearchSessionManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, PostSearchSession] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="post-search")

    def start(
        self,
        *,
        user_id: str,
        post_search_id: str,
        limit: int,
        min_score: int = 0,
        target_found: int = 1,
        account_label: str | None,
        search_run_id: str | None = None,
    ) -> PostSearchSession:
        with self._lock:
            session_id = str(uuid.uuid4())
            sess = PostSearchSession(
                session_id=session_id,
                user_id=user_id,
                post_search_id=post_search_id,
                search_run_id=search_run_id,
                status="running",
                message="Post search started.",
            )
            self._sessions[session_id] = sess
            fut = self._executor.submit(
                self._run,
                sess.session_id,
                post_search_id,
                limit,
                min_score,
                target_found,
                account_label,
                search_run_id,
            )
            sess.future = fut
            return sess

    def owns(self, *, user_id: str, session_id: str) -> bool:
        with self._lock:
            sess = self._sessions.get(session_id)
            return sess is not None and sess.user_id == user_id

    def get(self, *, user_id: str, session_id: str) -> PostSearchSession | None:
        with self._lock:
            sess = self._sessions.get(session_id)
            return None if sess is None or sess.user_id != user_id else sess

    def _update(
        self,
        session_id: str,
        *,
        status: RunStatus | None = None,
        message: str | None = None,
    ) -> None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return
            if status is not None:
                sess.status = status
            if message is not None:
                sess.message = message

    def _worker_root(self) -> Path:
        """
        Resolve worker root directory reliably.

        Do not depend on a fixed parents[N] depth, because the package can be
        executed from different layouts (editable installs, copied sources, etc).
        """
        here = Path(__file__).resolve()
        candidates = [here, *here.parents]
        found = next((p for p in candidates if (p / "run_post_search.py").exists()), None)
        return found if found is not None else here.parents[5]

    def _run(
        self,
        session_id: str,
        post_search_id: str,
        limit: int,
        min_score: int,
        target_found: int,
        account_label: str | None,
        search_run_id: str | None,
    ) -> None:
        worker_root = self._worker_root()
        script = worker_root / "run_post_search.py"
        try:
            if not script.exists():
                self._update(session_id, status="error", message=f"Script not found: {script}")
                return

            env: dict[str, str] = dict(os.environ)
            # Bind run to the requesting user (used by worker Storage layer).
            sess_any: Any = self._sessions[session_id]
            env["STORAGE_USER_ID"] = str(sess_any.user_id)
            if account_label:
                env["STORAGE_ACCOUNT_LABEL"] = account_label
            if search_run_id:
                env["SEARCH_RUN_ID"] = search_run_id

            argv = [
                sys.executable,
                str(script),
                "--post-search-id",
                post_search_id,
                "--limit",
                str(limit),
                "--min-score",
                str(min_score),
                "--target-found",
                str(target_found),
            ]

            import subprocess  # noqa: PLC0415

            # Capture output so we can surface the exact error text to the frontend.
            proc = subprocess.run(
                argv,
                cwd=str(worker_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            output = (proc.stdout or "").rstrip()
            if output:
                print(output)
            code = int(proc.returncode)
            if code == 0:
                self._update(session_id, status="done", message="Post search completed.")
            else:
                fallback = f"Post search failed with exit code {code}."
                if code == LLM_CONNECT_FAILED_EXIT_CODE:
                    fallback = (
                        "Не удалось подключиться к LLM. Поиск постов не запущен. "
                        "Уже выбранные посты не изменены."
                    )
                msg = client_failure_message(output, fallback=fallback)
                self._finalize_run(search_run_id, msg)
                self._update(session_id, status="error", message=msg)
        except Exception as e:
            detail = str(e).splitlines()[0] if str(e).strip() else type(e).__name__
            tb = traceback.format_exc(limit=10)
            print(tb)
            self._finalize_run(search_run_id, f"ERROR: {detail}")
            self._update(session_id, status="error", message=f"ERROR: {detail}")

    @staticmethod
    def _finalize_run(search_run_id: str | None, error: str | None) -> None:
        if not search_run_id:
            return
        try:
            from ..search_runs.service import finalize_run_error  # noqa: PLC0415

            finalize_run_error(run_id=search_run_id, error=error)
        except Exception:
            pass

