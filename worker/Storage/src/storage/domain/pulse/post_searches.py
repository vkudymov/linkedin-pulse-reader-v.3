from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list, expect_single

from .models import PostSearchRow


class PostSearchRepository:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._type_id_posts: str | None = None

    def _posts_type_id(self) -> str:
        if self._type_id_posts:
            return self._type_id_posts
        resp = self._client.table("search_types").select("id").eq("code", "posts").maybe_single().execute()
        row = getattr(resp, "data", None)
        tid = str(row.get("id") or "") if isinstance(row, dict) else ""
        if not tid:
            raise RuntimeError("Missing search_types row for code=posts")
        self._type_id_posts = tid
        return tid

    @staticmethod
    def _attach_post_prompts(row: dict[str, Any]) -> dict[str, Any]:
        prompts = row.get("prompts")
        search_prompt: str = ""
        comment_prompt: str | None = None
        if isinstance(prompts, list):
            for p in prompts:
                if not isinstance(p, dict):
                    continue
                role = p.get("role")
                body = p.get("body")
                if not isinstance(body, str):
                    continue
                if role == "search":
                    search_prompt = body
                elif role == "comment":
                    comment_prompt = body
        out = dict(row)
        out.pop("prompts", None)
        out.pop("search_type_id", None)
        out["search_prompt"] = search_prompt
        out["comment_prompt"] = comment_prompt
        return out

    def list_by_user(self, *, user_id: str) -> list[PostSearchRow]:
        resp = (
            self._client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,created_at,updated_at,search_tariff_id,"
                "email_report_enabled,email_report_format,account_label,prompts(role,body)"
            )
            .eq("user_id", user_id)
            .eq("search_type_id", self._posts_type_id())
            .order("created_at", desc=False)
            .execute()
        )
        rows = expect_list(resp)
        return [self._attach_post_prompts(r) for r in rows]  # type: ignore[return-value]

    def get_by_id(self, *, post_search_id: str) -> PostSearchRow | None:
        resp = (
            self._client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,created_at,updated_at,search_tariff_id,"
                "email_report_enabled,email_report_format,account_label,search_type_id,prompts(role,body)"
            )
            .eq("id", post_search_id)
            .maybe_single()
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, dict):
            return None
        if str(data.get("search_type_id") or "") != self._posts_type_id():
            return None
        return self._attach_post_prompts(data)  # type: ignore[return-value]

    def create(
        self,
        *,
        user_id: str,
        title: str,
        search_prompt: str,
        comment_prompt: str | None,
        account_label: str | None = None,
        search_tariff_id: str | None = None,
        status: str = "active",
    ) -> PostSearchRow:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "search_type_id": self._posts_type_id(),
            "title": title,
            "account_label": account_label,
            "search_tariff_id": search_tariff_id,
            "status": status,
            "last_run_at": None,
        }
        resp = self._client.table("searches").insert(payload).select("*").maybe_single().execute()
        created = expect_single(resp)  # type: ignore[assignment]
        try:
            rows: list[dict[str, Any]] = [{"search_id": created["id"], "role": "search", "body": search_prompt}]
            if isinstance(comment_prompt, str) and comment_prompt:
                rows.append({"search_id": created["id"], "role": "comment", "body": comment_prompt})
            self._client.table("prompts").insert(rows).execute()
        except Exception:
            try:
                self._client.table("searches").delete().eq("id", created["id"]).execute()
            except Exception:
                pass
            raise

        created["prompts"] = [{"role": "search", "body": search_prompt}] + (
            [{"role": "comment", "body": comment_prompt}] if comment_prompt else []
        )
        return self._attach_post_prompts(created)  # type: ignore[return-value]

    def update(
        self,
        *,
        post_search_id: str,
        title: str | None = None,
        search_prompt: str | None = None,
        comment_prompt: str | None = None,
        account_label: str | None = None,
        status: str | None = None,
        last_run_at: str | None = None,
        email_report_enabled: bool | None = None,
        email_report_format: str | None = None,
    ) -> PostSearchRow:
        now = datetime.now(UTC).isoformat()
        payload: dict[str, Any] = {"updated_at": now}
        if title is not None:
            payload["title"] = title
        if account_label is not None:
            payload["account_label"] = account_label
        if status is not None:
            payload["status"] = status
        if last_run_at is not None:
            payload["last_run_at"] = last_run_at
        if email_report_enabled is not None:
            payload["email_report_enabled"] = bool(email_report_enabled)
        if email_report_format is not None:
            payload["email_report_format"] = email_report_format
        resp = (
            self._client.table("searches")
            .update(payload)
            .eq("id", post_search_id)
            .select("*")
            .execute()
        )
        updated = expect_single(resp)  # type: ignore[assignment]

        if search_prompt is not None:
            self._client.table("prompts").upsert(
                [{"search_id": post_search_id, "role": "search", "body": search_prompt}],
                on_conflict="search_id,role",
            ).execute()
        if comment_prompt is not None:
            if comment_prompt:
                self._client.table("prompts").upsert(
                    [{"search_id": post_search_id, "role": "comment", "body": comment_prompt}],
                    on_conflict="search_id,role",
                ).execute()
            else:
                # empty string -> delete optional prompt
                self._client.table("prompts").delete().eq("search_id", post_search_id).eq("role", "comment").execute()

        p_resp = self._client.table("prompts").select("role,body").eq("search_id", post_search_id).execute()
        p_rows = expect_list(p_resp)
        updated["prompts"] = p_rows
        return self._attach_post_prompts(updated)  # type: ignore[return-value]

    def delete(self, *, post_search_id: str) -> None:
        self._client.table("searches").delete().eq("id", post_search_id).execute()

