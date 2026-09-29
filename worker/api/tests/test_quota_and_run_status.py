from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from pulse_api.search_quota import (
    SearchQuotaError,
    charge_post_search_quota_after_start,
    increment_post_search_run_count,
)
from pulse_api.search_runs.client_message import client_failure_message, short_stored_error
from pulse_api.search_runs.status import LOST_MESSAGE, poll_search_run


class _Rpc:
    def __init__(self, client: "_QuotaClient") -> None:
        self._client = client

    def execute(self) -> SimpleNamespace:
        if self._client.error is not None:
            raise self._client.error
        self._client.calls += 1
        return SimpleNamespace(data=self._client.calls)


class _QuotaClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls = 0
        self.error = error

    def rpc(self, name: str, params: dict[str, Any]) -> _Rpc:
        assert name == "increment_post_search_run_count"
        assert params["p_user_id"] == "user-1"
        return _Rpc(self)


def test_counter_increments_only_after_successful_start() -> None:
    client = _QuotaClient()

    def start() -> str:
        assert client.calls == 0
        return "session"

    result = charge_post_search_quota_after_start(client=client, user_id="user-1", start=start)
    assert result == "session"
    assert client.calls == 1


def test_failed_start_does_not_increment() -> None:
    client = _QuotaClient()

    def start() -> str:
        raise RuntimeError("search did not start")

    with pytest.raises(RuntimeError, match="did not start"):
        charge_post_search_quota_after_start(client=client, user_id="user-1", start=start)
    assert client.calls == 0


def test_increment_error_is_not_swallowed() -> None:
    client = _QuotaClient(error=RuntimeError("db password hunter2 li_at=abc"))
    with pytest.raises(SearchQuotaError) as exc:
        increment_post_search_run_count(client=client, user_id="user-1")
    assert exc.value.status_code == 500
    assert "hunter2" not in exc.value.detail
    assert "li_at" not in exc.value.detail


def test_blocked_user_is_reported() -> None:
    client = _QuotaClient(error=RuntimeError("user_blocked"))
    with pytest.raises(SearchQuotaError) as exc:
        increment_post_search_run_count(client=client, user_id="user-1")
    assert exc.value.status_code == 403


class _Runs:
    def __init__(self, row: dict[str, Any] | None, *, lose_race: bool = False) -> None:
        self.row = row
        self.lose_race = lose_race
        self.lost_calls: list[tuple[str, str]] = []

    def get_by_session_id(self, *, user_id: str, session_id: str) -> dict[str, Any] | None:
        row = self.row
        if row is None:
            return None
        if row.get("user_id") != user_id or row.get("session_id") != session_id:
            return None
        return dict(row)

    def mark_lost_if_running(self, *, run_id: str, error: str) -> dict[str, Any] | None:
        self.lost_calls.append((run_id, error))
        if self.row is None:
            return None
        if self.lose_race:
            self.row = {**self.row, "status": "done", "error": None}
            return None
        self.row = {**self.row, "status": "lost", "error": error}
        return dict(self.row)


def _row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "run-1",
        "user_id": "user-1",
        "session_id": "sess-1",
        "status": "running",
        "error": None,
        "kind": "post",
    }
    base.update(overrides)
    return base


def test_missing_session_is_unknown() -> None:
    assert (
        poll_search_run(
            user_id="user-1",
            session_id="missing",
            executor_alive=False,
            repo=_Runs(None),
        )
        is None
    )


def test_running_without_executor_becomes_lost() -> None:
    repo = _Runs(_row())
    polled = poll_search_run(
        user_id="user-1",
        session_id="sess-1",
        executor_alive=False,
        repo=repo,
    )
    assert polled is not None
    assert polled["status"] == "lost"
    assert polled["message"] == LOST_MESSAGE
    assert repo.lost_calls == [("run-1", LOST_MESSAGE)]


def test_live_executor_keeps_running() -> None:
    repo = _Runs(_row())
    polled = poll_search_run(
        user_id="user-1",
        session_id="sess-1",
        executor_alive=True,
        repo=repo,
    )
    assert polled is not None
    assert polled["status"] == "running"
    assert repo.lost_calls == []


def test_lost_race_returns_finished_status() -> None:
    repo = _Runs(_row(), lose_race=True)
    polled = poll_search_run(
        user_id="user-1",
        session_id="sess-1",
        executor_alive=False,
        repo=repo,
    )
    assert polled is not None
    assert polled["status"] == "done"
    assert repo.row is not None
    assert repo.row["status"] == "done"


def test_raw_stdout_is_not_a_client_message() -> None:
    blob = "worker log line\n" + ("x" * 4000)
    message = client_failure_message(blob, fallback="Post search failed.")
    assert message == "Post search failed."
    assert "xxxx" not in message

    stored = short_stored_error(blob, fallback="Search failed.")
    assert stored == "Search failed."
    assert len(stored) < 240


def test_error_line_is_the_client_message() -> None:
    output = "noise\nERROR: login required\n" + ("y" * 3000)
    assert client_failure_message(output, fallback="fallback") == "ERROR: login required"
