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

RunStatus = Literal["running", "done", "error"]


@dataclass(slots=True)
class PostSearchSession:
    session_id: str
    user_id: str
    status: RunStatus
    message: str | None
    exit_code: int | None = None
    future: Future[None] | None = None


class PostSearchSessionManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, PostSearchSession] = {}
        self._active_by_user: dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="post-search")

    def start(self, *, user_id: str, limit: int, account_label: str | None) -> PostSearchSession:
        with self._lock:
            session_id = str(uuid.uuid4())
            sess = PostSearchSession(
                session_id=session_id,
                user_id=user_id,
                status="running",
                message="Post search started.",
                exit_code=None,
            )
            self._sessions[session_id] = sess
            self._active_by_user[user_id] = session_id
            fut = self._executor.submit(self._run, sess.session_id, limit, account_label)
            sess.future = fut
            return sess

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
        exit_code: int | None = None,
    ) -> None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return
            if status is not None:
                sess.status = status
            if message is not None:
                sess.message = message
            if exit_code is not None:
                sess.exit_code = exit_code

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

    def _run(self, session_id: str, limit: int, account_label: str | None) -> None:
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

            argv = [sys.executable, str(script), "--limit", str(limit)]

            import subprocess  # noqa: PLC0415

            proc = subprocess.run(argv, cwd=str(worker_root), env=env)
            code = int(proc.returncode)
            if code == 0:
                self._update(session_id, status="done", message="Post search completed.", exit_code=code)
            else:
                self._update(
                    session_id,
                    status="error",
                    message=f"Post search failed with exit code {code}.",
                    exit_code=code,
                )
        except Exception as e:
            detail = str(e).splitlines()[0] if str(e).strip() else type(e).__name__
            tb = traceback.format_exc(limit=10)
            self._update(session_id, status="error", message=f"{detail}\n\n{tb}")

