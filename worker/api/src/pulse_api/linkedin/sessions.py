from __future__ import annotations

import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event, Lock
from typing import Any, Literal

from ..settings import get_settings
from .persist import persist_cookies

LoginStatus = Literal[
    "pending",
    "awaiting_user",
    "checkpoint",
    "completed",
    "failed",
    "cancelled",
]


@dataclass(slots=True)
class LoginSession:
    session_id: str
    user_id: str
    status: LoginStatus
    message: str | None
    linkedin_account_id: str | None
    cancel_event: Event
    future: Future[None] | None = None


class LoginSessionManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, LoginSession] = {}
        self._active_by_user: dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="linkedin-auth")

    def start(
        self,
        *,
        user_id: str,
        method: str,
        identifier: str | None,
        password: str | None,
        label: str | None,
    ) -> LoginSession:
        with self._lock:
            # Cancel previous session for that user (best-effort).
            if (prev_id := self._active_by_user.get(user_id)) and prev_id in self._sessions:
                prev = self._sessions[prev_id]
                prev.cancel_event.set()
                prev.status = "cancelled"
                prev.message = "Cancelled by a newer login request."

            session_id = str(uuid.uuid4())
            sess = LoginSession(
                session_id=session_id,
                user_id=user_id,
                status="pending",
                message="Starting LinkedIn login flow.",
                linkedin_account_id=None,
                cancel_event=Event(),
            )
            self._sessions[session_id] = sess
            self._active_by_user[user_id] = session_id

            fut = self._executor.submit(
                self._run_session,
                sess.session_id,
                method,
                identifier,
                password,
                label,
            )
            sess.future = fut
            return sess

    def get(self, *, user_id: str, session_id: str) -> LoginSession | None:
        with self._lock:
            sess = self._sessions.get(session_id)
            return None if sess is None or sess.user_id != user_id else sess

    def cancel(self, *, user_id: str, session_id: str) -> LoginSession | None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None or sess.user_id != user_id:
                return None
            sess.cancel_event.set()
            sess.status = "cancelled"
            sess.message = "Cancelled by user."
            if self._active_by_user.get(user_id) == session_id:
                self._active_by_user.pop(user_id, None)
            return sess

    def _update(
        self,
        session_id: str,
        *,
        status: LoginStatus | None = None,
        message: str | None = None,
        linkedin_account_id: str | None = None,
    ) -> None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                return
            if sess.status == "cancelled":
                # Do not override a cancelled session from a background thread.
                if linkedin_account_id is not None:
                    sess.linkedin_account_id = linkedin_account_id
                return
            if status is not None:
                sess.status = status
            if message is not None:
                sess.message = message
            if linkedin_account_id is not None:
                sess.linkedin_account_id = linkedin_account_id

    def _run_session(
        self,
        session_id: str,
        method: str,
        identifier: str | None,
        password: str | None,
        label: str | None,
    ) -> None:
        settings = get_settings()
        sess = self._sessions[session_id]

        def _on_checkpoint() -> None:
            self._update(
                session_id,
                status="checkpoint",
                message="LinkedIn требует verification (checkpoint). Завершите проверку в открытом окне.",
            )

        self._update(
            session_id,
            status="awaiting_user",
            message="Завершите вход в открытом окне Chromium. После редиректа на /feed cookies будут сохранены.",
        )

        try:
            from linkedin_client import LinkedInClient, LinkedInClientConfig  # type: ignore[import-not-found]
            from linkedin_client.auth.methods import LoginMethod  # type: ignore[import-not-found]
            from linkedin_client.browser import BrowserConfig  # type: ignore[import-not-found]
            from linkedin_client.exceptions import (
                LoginCancelledError,
                LoginCheckpointError,
                LoginTimeoutError,
            )  # type: ignore[import-not-found]

            cfg = LinkedInClientConfig(
                browser=BrowserConfig(
                    headless=False,
                    timeout_ms=settings.linkedin_auth_timeout_ms,
                    channel=settings.playwright_channel,
                    user_data_dir=settings.playwright_user_data_dir,
                )
            )

            with LinkedInClient(config=cfg) as client:
                cookies: list[dict[str, Any]] = client.login_and_get_cookies(
                    method=LoginMethod(method),
                    identifier=identifier,
                    password=password,
                    cancelled=sess.cancel_event.is_set,
                    on_checkpoint=_on_checkpoint,
                )

            if sess.cancel_event.is_set():
                self._update(session_id, status="cancelled", message="Cancelled by user.")
                return

            account_id = persist_cookies(user_id=sess.user_id, cookies=cookies, label=label)
            self._update(
                session_id,
                status="completed",
                message="Cookies сохранены в Supabase.",
                linkedin_account_id=account_id,
            )
        except LoginCancelledError:
            self._update(session_id, status="cancelled", message="Cancelled by user.")
        except LoginCheckpointError:
            # This should not happen when on_checkpoint is provided, but keep as a fallback.
            self._update(
                session_id,
                status="checkpoint",
                message="LinkedIn требует verification (checkpoint). Завершите проверку в открытом окне.",
            )
        except LoginTimeoutError as e:
            self._update(session_id, status="failed", message=str(e))
        except Exception as e:
            detail = str(e).splitlines()[0] if str(e).strip() else type(e).__name__
            tb = traceback.format_exc(limit=10)
            self._update(
                session_id,
                status="failed",
                message=f"{detail}\n\n{tb}",
            )

