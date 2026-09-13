from __future__ import annotations

import os
import re
import sys
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Literal

RunStatus = Literal["running", "done", "error"]
LLM_CONNECT_FAILED_EXIT_CODE = 2

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _extract_error_line(output: str) -> str | None:
    cleaned = _ANSI_RE.sub("", output or "")
    for line in cleaned.splitlines():
        candidate = line.strip()
        if candidate.startswith("ERROR:"):
            return candidate
    return None


@dataclass(slots=True)
class JobSearchSession:
    session_id: str
    user_id: str
    status: RunStatus
    message: str | None
    future: Future[None] | None = None


class JobSearchSessionManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, JobSearchSession] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="job-search")

    def start(
        self,
        *,
        user_id: str,
        job_search_id: str,
        limit: int,
        account_label: str | None,
    ) -> JobSearchSession:
        with self._lock:
            session_id = str(uuid.uuid4())
            sess = JobSearchSession(
                session_id=session_id,
                user_id=user_id,
                status="running",
                message="Job search started.",
            )
            self._sessions[session_id] = sess
            fut = self._executor.submit(self._run, sess.session_id, job_search_id, limit, account_label)
            sess.future = fut
            return sess

    def get(self, *, user_id: str, session_id: str) -> JobSearchSession | None:
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
        here = Path(__file__).resolve()
        candidates = [here, *here.parents]
        found = next((p for p in candidates if (p / "run_job_search.py").exists()), None)
        return found if found is not None else here.parents[5]

    def _run(self, session_id: str, job_search_id: str, limit: int, account_label: str | None) -> None:
        worker_root = self._worker_root()
        script = worker_root / "run_job_search.py"
        try:
            if not script.exists():
                self._update(session_id, status="error", message=f"Script not found: {script}")
                return

            env: dict[str, str] = dict(os.environ)
            sess_any: Any = self._sessions[session_id]
            env["STORAGE_USER_ID"] = str(sess_any.user_id)
            if account_label:
                env["STORAGE_ACCOUNT_LABEL"] = account_label

            argv = [
                sys.executable,
                str(script),
                "--job-search-id",
                str(job_search_id),
                "--limit",
                str(limit),
            ]

            import subprocess  # noqa: PLC0415

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
                self._update(session_id, status="done", message="Job search completed.")
            else:
                error_line = _extract_error_line(output)
                if code == LLM_CONNECT_FAILED_EXIT_CODE:
                    self._update(
                        session_id,
                        status="error",
                        message=(error_line or "Не удалось подключиться к LLM. Поиск вакансий не запущен."),
                    )
                    return
                self._update(
                    session_id,
                    status="error",
                    message=(
                        error_line
                        or (output[-4000:] if output else f"Job search failed with exit code {code}.")
                    ),
                )
        except Exception as e:
            detail = str(e).splitlines()[0] if str(e).strip() else type(e).__name__
            tb = traceback.format_exc(limit=10)
            print(tb)
            self._update(session_id, status="error", message=f"ERROR: {detail}")

