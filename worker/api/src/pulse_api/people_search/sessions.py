from __future__ import annotations

import json
import os
import sys
import time
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from ..search_runs.client_message import client_failure_message

# #region agent log
_DEBUG_LOG = Path("/Users/vladimirkudymov/Work/linkedin-pulse-reader-v.3/.cursor/debug-8b59cb.log")


def _agent_log(*, hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    try:
        payload = {
            "sessionId": "8b59cb",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


# #endregion

RunStatus = Literal["running", "done", "error"]
LLM_CONNECT_FAILED_EXIT_CODE = 2


@dataclass(slots=True)
class PeopleSearchSession:
    session_id: str
    user_id: str
    search_run_id: str | None
    status: RunStatus
    message: str | None
    future: Future[None] | None = None


class PeopleSearchSessionManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, PeopleSearchSession] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="people-search")

    def start(
        self,
        *,
        user_id: str,
        people_search_id: str,
        limit: int,
        min_score: int = 0,
        target_found: int = 1,
        account_label: str | None,
        search_run_id: str | None = None,
    ) -> PeopleSearchSession:
        with self._lock:
            session_id = str(uuid.uuid4())
            sess = PeopleSearchSession(
                session_id=session_id,
                user_id=user_id,
                search_run_id=search_run_id,
                status="running",
                message="People search started.",
            )
            self._sessions[session_id] = sess
            fut = self._executor.submit(
                self._run,
                sess.session_id,
                people_search_id,
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

    def get(self, *, user_id: str, session_id: str) -> PeopleSearchSession | None:
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
        found = next((p for p in candidates if (p / "run_people_search.py").exists()), None)
        return found if found is not None else here.parents[5]

    def _run(
        self,
        session_id: str,
        people_search_id: str,
        limit: int,
        min_score: int,
        target_found: int,
        account_label: str | None,
        search_run_id: str | None,
    ) -> None:
        worker_root = self._worker_root()
        script = worker_root / "run_people_search.py"
        try:
            if not script.exists():
                self._update(session_id, status="error", message=f"Script not found: {script}")
                return

            env: dict[str, str] = dict(os.environ)
            sess_any: Any = self._sessions[session_id]
            env["STORAGE_USER_ID"] = str(sess_any.user_id)
            if account_label:
                env["STORAGE_ACCOUNT_LABEL"] = account_label
            if search_run_id:
                env["SEARCH_RUN_ID"] = search_run_id

            argv = [
                sys.executable,
                str(script),
                "--people-search-id",
                people_search_id,
                "--limit",
                str(limit),
                "--min-score",
                str(min_score),
                "--target-found",
                str(target_found),
            ]

            import subprocess  # noqa: PLC0415

            people_src = worker_root / "PeopleSearch" / "src"
            people_pkg = worker_root.parent / "packages" / "linkedin-search-people" / "src"
            # #region agent log
            probe = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import importlib.util as u; print(u.find_spec('people_search') is not None); print(u.find_spec('linkedin_search_people') is not None); print(u.find_spec('job_search') is not None)",
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            _agent_log(
                hypothesis_id="A",
                location="people_search/sessions.py:_run",
                message="pre-run import probe",
                data={
                    "executable": sys.executable,
                    "cwd": str(worker_root),
                    "script": str(script),
                    "pythonpath": env.get("PYTHONPATH", ""),
                    "people_src_exists": people_src.is_dir(),
                    "people_pkg_exists": people_pkg.is_dir(),
                    "probe_out": (probe.stdout or "").strip()[:400],
                    "probe_code": probe.returncode,
                },
            )
            # #endregion

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
            code = proc.returncode
            # #region agent log
            _agent_log(
                hypothesis_id="B",
                location="people_search/sessions.py:_run",
                message="subprocess finished",
                data={
                    "code": code,
                    "output_head": output[:800],
                    "has_people_search_modulenotfound": "No module named 'people_search'" in output,
                    "has_linkedin_people_modulenotfound": "No module named 'linkedin_search_people'" in output,
                },
            )
            # #endregion
            if code == 0:
                self._update(session_id, status="done", message="People search completed.")
            else:
                fallback = f"People search failed with exit code {code}."
                if code == LLM_CONNECT_FAILED_EXIT_CODE:
                    fallback = "Не удалось подключиться к LLM. Поиск людей не запущен."
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
