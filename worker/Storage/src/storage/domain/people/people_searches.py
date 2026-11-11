from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list, expect_single

from .models import PeopleSearchRow


class PeopleSearchRepository:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._type_id: str | None = None

    def _people_type_id(self) -> str:
        if self._type_id:
            return self._type_id
        resp = (
            self._client.table("search_types")
            .select("id")
            .eq("code", "people")
            .maybe_single()
            .execute()
        )
        row = getattr(resp, "data", None)
        tid = str(row.get("id") or "") if isinstance(row, dict) else ""
        if not tid:
            raise RuntimeError("Missing search_types row for code=people")
        self._type_id = tid
        return tid

    @staticmethod
    def _attach_prompt(row: dict[str, Any]) -> dict[str, Any]:
        fp = row.get("people_prompt")
        prompt = ""
        if isinstance(fp, dict):
            v = fp.get("body")
            if isinstance(v, str):
                prompt = v
        out = dict(row)
        out.pop("people_prompt", None)
        out.pop("search_type_id", None)
        out["prompt"] = prompt
        return out

    def list_by_user(self, *, user_id: str) -> list[PeopleSearchRow]:
        resp = (
            self._client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,created_at,updated_at,search_tariff_id,"
                "search_query,linkedin_filters,"
                "people_prompt:prompts!searches_people_prompt_id_fkey(body)"
            )
            .eq("user_id", user_id)
            .eq("search_type_id", self._people_type_id())
            .order("created_at", desc=False)
            .execute()
        )
        rows = expect_list(resp)
        return [self._attach_prompt(r) for r in rows]  # type: ignore[return-value]

    def get_by_id(self, *, people_search_id: str) -> PeopleSearchRow | None:
        resp = (
            self._client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,created_at,updated_at,search_tariff_id,"
                "search_query,linkedin_filters,search_type_id,people_prompt_id,"
                "people_prompt:prompts!searches_people_prompt_id_fkey(id,body)"
            )
            .eq("id", people_search_id)
            .maybe_single()
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, dict):
            return None
        if str(data.get("search_type_id") or "") != self._people_type_id():
            return None
        return self._attach_prompt(data)  # type: ignore[return-value]

    def update(self, *, people_search_id: str, last_run_at: str | None = None) -> PeopleSearchRow:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {"updated_at": now}
        if last_run_at is not None:
            payload["last_run_at"] = last_run_at
        resp = (
            self._client.table("searches")
            .update(payload)
            .eq("id", people_search_id)
            .select("*")
            .execute()
        )
        updated = expect_single(resp)  # type: ignore[assignment]
        return self._attach_prompt(updated)  # type: ignore[return-value]
