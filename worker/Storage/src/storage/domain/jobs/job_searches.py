from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list, expect_single

from .models import JobSearchRow


class JobSearchRepository:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._type_id_jobs: str | None = None

    def _jobs_type_id(self) -> str:
        if self._type_id_jobs:
            return self._type_id_jobs
        resp = self._client.table("search_types").select("id").eq("code", "jobs").maybe_single().execute()
        row = getattr(resp, "data", None)
        tid = str(row.get("id") or "") if isinstance(row, dict) else ""
        if not tid:
            raise RuntimeError("Missing search_types row for code=jobs")
        self._type_id_jobs = tid
        return tid

    @staticmethod
    def _attach_filter_prompt(row: dict[str, Any]) -> dict[str, Any]:
        prompts = row.get("prompts")
        filter_prompt: str = ""
        if isinstance(prompts, list):
            for p in prompts:
                if isinstance(p, dict) and p.get("role") == "filter":
                    v = p.get("body")
                    if isinstance(v, str):
                        filter_prompt = v
                        break
        out = dict(row)
        out.pop("prompts", None)
        out.pop("search_type_id", None)
        out["filter_prompt"] = filter_prompt
        return out

    def list_by_user(self, *, user_id: str) -> list[JobSearchRow]:
        resp = (
            self._client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,created_at,updated_at,search_tariff_id,"
                "email_report_enabled,email_report_format,search_query,location,linkedin_filters,prompts(role,body)"
            )
            .eq("user_id", user_id)
            .eq("search_type_id", self._jobs_type_id())
            .order("created_at", desc=False)
            .execute()
        )
        rows = expect_list(resp)
        return [self._attach_filter_prompt(r) for r in rows]  # type: ignore[return-value]

    def get_by_id(self, *, job_search_id: str) -> JobSearchRow | None:
        resp = (
            self._client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,created_at,updated_at,search_tariff_id,"
                "email_report_enabled,email_report_format,search_query,location,linkedin_filters,search_type_id,prompts(role,body)"
            )
            .eq("id", job_search_id)
            .maybe_single()
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, dict):
            return None
        if str(data.get("search_type_id") or "") != self._jobs_type_id():
            return None
        return self._attach_filter_prompt(data)  # type: ignore[return-value]

    def create(
        self,
        *,
        user_id: str,
        title: str,
        search_query: str,
        location: str | None,
        filter_prompt: str,
        status: str = "active",
        linkedin_filters: dict[str, Any] | None = None,
        search_tariff_id: str | None = None,
    ) -> JobSearchRow:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "search_type_id": self._jobs_type_id(),
            "title": title,
            "search_query": search_query,
            "location": location,
            "search_tariff_id": search_tariff_id,
            "status": status,
            "last_run_at": None,
        }
        if linkedin_filters is not None:
            payload["linkedin_filters"] = linkedin_filters
        resp = self._client.table("searches").insert(payload).select("*").maybe_single().execute()
        created = expect_single(resp)  # type: ignore[assignment]
        try:
            self._client.table("prompts").insert(
                {
                    "search_id": created["id"],
                    "role": "filter",
                    "body": filter_prompt,
                }
            ).execute()
        except Exception:
            try:
                self._client.table("searches").delete().eq("id", created["id"]).execute()
            except Exception:
                pass
            raise
        created["prompts"] = [{"role": "filter", "body": filter_prompt}]
        return self._attach_filter_prompt(created)  # type: ignore[return-value]

    def update(
        self,
        *,
        job_search_id: str,
        title: str | None = None,
        search_query: str | None = None,
        location: str | None = None,
        filter_prompt: str | None = None,
        status: str | None = None,
        last_run_at: str | None = None,
        linkedin_filters: dict[str, Any] | None = None,
        email_report_enabled: bool | None = None,
        email_report_format: str | None = None,
    ) -> JobSearchRow:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {"updated_at": now}
        if title is not None:
            payload["title"] = title
        if search_query is not None:
            payload["search_query"] = search_query
        if location is not None:
            payload["location"] = location
        if status is not None:
            payload["status"] = status
        if last_run_at is not None:
            payload["last_run_at"] = last_run_at
        if linkedin_filters is not None:
            payload["linkedin_filters"] = linkedin_filters
        if email_report_enabled is not None:
            payload["email_report_enabled"] = bool(email_report_enabled)
        if email_report_format is not None:
            payload["email_report_format"] = email_report_format

        resp = (
            self._client.table("searches")
            .update(payload)
            .eq("id", job_search_id)
            .select("*")
            .execute()
        )
        updated = expect_single(resp)  # type: ignore[assignment]

        if filter_prompt is not None:
            self._client.table("prompts").upsert(
                [{"search_id": job_search_id, "role": "filter", "body": filter_prompt}],
                on_conflict="search_id,role",
            ).execute()

        p_resp = self._client.table("prompts").select("role,body").eq("search_id", job_search_id).execute()
        p_rows = expect_list(p_resp)
        updated["prompts"] = p_rows
        return self._attach_filter_prompt(updated)  # type: ignore[return-value]

    def delete(self, *, job_search_id: str) -> None:
        self._client.table("searches").delete().eq("id", job_search_id).execute()

