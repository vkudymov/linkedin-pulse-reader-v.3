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
        search_prompt: str = ""
        comment_prompt: str | None = None
        sp = row.get("search_prompt")
        cp = row.get("comment_prompt")
        if isinstance(sp, dict) and isinstance(sp.get("body"), str):
            search_prompt = str(sp.get("body") or "")
        if isinstance(cp, dict) and isinstance(cp.get("body"), str):
            comment_prompt = str(cp.get("body") or "") or None
        out = dict(row)
        out.pop("search_prompt", None)
        out.pop("comment_prompt", None)
        out.pop("search_type_id", None)
        out["search_prompt"] = search_prompt
        out["comment_prompt"] = comment_prompt
        return out

    def list_by_user(self, *, user_id: str) -> list[PostSearchRow]:
        resp = (
            self._client.table("searches")
            .select(
                "id,user_id,title,status,last_run_at,created_at,updated_at,search_tariff_id,"
                "email_report_enabled,email_report_format,account_label,"
                "search_prompt:prompts!searches_search_prompt_id_fkey(body),"
                "comment_prompt:prompts!searches_comment_prompt_id_fkey(body)"
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
                "email_report_enabled,email_report_format,account_label,search_type_id,"
                "search_prompt_id,comment_prompt_id,"
                "search_prompt:prompts!searches_search_prompt_id_fkey(id,body),"
                "comment_prompt:prompts!searches_comment_prompt_id_fkey(id,body)"
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
            sp = (
                self._client.table("prompts")
                .insert({"user_id": user_id, "role": "search", "title": title, "body": search_prompt})
                .select("id,body")
                .maybe_single()
                .execute()
            )
            sp_row = getattr(sp, "data", None)
            sp_id = str(sp_row.get("id") or "") if isinstance(sp_row, dict) else ""
            if not sp_id:
                raise RuntimeError("search prompt insert failed")

            cp_id: str | None = None
            if isinstance(comment_prompt, str) and comment_prompt:
                cp = (
                    self._client.table("prompts")
                    .insert({"user_id": user_id, "role": "comment", "title": title, "body": comment_prompt})
                    .select("id,body")
                    .maybe_single()
                    .execute()
                )
                cp_row = getattr(cp, "data", None)
                cp_id = str(cp_row.get("id") or "") if isinstance(cp_row, dict) else None

            self._client.table("searches").update({"search_prompt_id": sp_id, "comment_prompt_id": cp_id}).eq("id", created["id"]).execute()
            created["search_prompt_id"] = sp_id
            created["comment_prompt_id"] = cp_id
            created["search_prompt"] = {"id": sp_id, "body": search_prompt}
            created["comment_prompt"] = {"id": cp_id, "body": comment_prompt} if cp_id else None
        except Exception:
            try:
                self._client.table("searches").delete().eq("id", created["id"]).execute()
            except Exception:
                pass
            raise
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
            sid = str(updated.get("user_id") or "")
            cur_pid = str(updated.get("search_prompt_id") or "")
            if cur_pid:
                self._client.table("prompts").update({"body": search_prompt}).eq("id", cur_pid).eq("user_id", sid).execute()
            else:
                p = (
                    self._client.table("prompts")
                    .insert({"user_id": sid, "role": "search", "title": str(updated.get("title") or "Search prompt"), "body": search_prompt})
                    .select("id")
                    .maybe_single()
                    .execute()
                )
                prow = getattr(p, "data", None)
                pid = str(prow.get("id") or "") if isinstance(prow, dict) else ""
                if pid:
                    self._client.table("searches").update({"search_prompt_id": pid}).eq("id", post_search_id).execute()
                    updated["search_prompt_id"] = pid
            updated["search_prompt"] = {"body": search_prompt}
        if comment_prompt is not None:
            sid = str(updated.get("user_id") or "")
            cur_pid = str(updated.get("comment_prompt_id") or "")
            if comment_prompt:
                if cur_pid:
                    self._client.table("prompts").update({"body": comment_prompt}).eq("id", cur_pid).eq("user_id", sid).execute()
                else:
                    p = (
                        self._client.table("prompts")
                        .insert({"user_id": sid, "role": "comment", "title": str(updated.get("title") or "Comment prompt"), "body": comment_prompt})
                        .select("id")
                        .maybe_single()
                        .execute()
                    )
                    prow = getattr(p, "data", None)
                    pid = str(prow.get("id") or "") if isinstance(prow, dict) else ""
                    if pid:
                        self._client.table("searches").update({"comment_prompt_id": pid}).eq("id", post_search_id).execute()
                        updated["comment_prompt_id"] = pid
                updated["comment_prompt"] = {"body": comment_prompt}
            else:
                # empty string -> unlink optional prompt (do not delete library prompt)
                self._client.table("searches").update({"comment_prompt_id": None}).eq("id", post_search_id).execute()
                updated["comment_prompt_id"] = None
                updated["comment_prompt"] = None
        return self._attach_post_prompts(updated)  # type: ignore[return-value]

    def delete(self, *, post_search_id: str) -> None:
        self._client.table("searches").delete().eq("id", post_search_id).execute()

