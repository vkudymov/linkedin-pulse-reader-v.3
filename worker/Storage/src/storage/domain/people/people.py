from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from storage.core.response import expect_list
from storage.errors import StorageResponseError

from .models import PersonRow


class PeopleRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def upsert_people(
        self,
        *,
        user_id: str,
        linkedin_account_id: str,
        people: list[dict[str, Any]],
    ) -> list[PersonRow]:
        now = datetime.now(UTC).isoformat()
        rows: list[dict[str, Any]] = []
        for p in people:
            if not isinstance(p, Mapping):
                continue
            source_key = p.get("source_key")
            profile_url = p.get("profile_url")
            if not isinstance(source_key, str) or not source_key.strip():
                continue
            if not isinstance(profile_url, str) or not profile_url.strip():
                continue
            skills = p.get("skills") if isinstance(p.get("skills"), list) else []
            experience = p.get("experience") if isinstance(p.get("experience"), list) else []
            education = p.get("education") if isinstance(p.get("education"), list) else []
            row: dict[str, Any] = {
                "user_id": user_id,
                "linkedin_account_id": linkedin_account_id,
                "source_key": source_key.strip(),
                "public_id": p.get("public_id") if isinstance(p.get("public_id"), str) else None,
                "profile_url": profile_url.strip(),
                "full_name": p.get("full_name") if isinstance(p.get("full_name"), str) else None,
                "headline": p.get("headline") if isinstance(p.get("headline"), str) else None,
                "location": p.get("location") if isinstance(p.get("location"), str) else None,
                "connection_degree": p.get("connection_degree")
                if isinstance(p.get("connection_degree"), str)
                else None,
                "about": p.get("about") if isinstance(p.get("about"), str) else None,
                "skills": skills,
                "current_company": p.get("current_company")
                if isinstance(p.get("current_company"), str)
                else None,
                "experience": experience,
                "education": education,
                "raw_extra": p.get("raw_extra") if isinstance(p.get("raw_extra"), dict) else None,
                "fetched_at": now,
                "updated_at": now,
            }
            avatar_url = p.get("avatar_url")
            if isinstance(avatar_url, str) and avatar_url.strip():
                row["avatar_url"] = avatar_url.strip()
            if p.get("about") or skills:
                row["enriched_at"] = now
            rows.append(row)

        if not rows:
            return []

        resp = (
            self._client.table("people")
            .upsert(rows, on_conflict="user_id,source_key")
            .select("*")
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise StorageResponseError("Expected list response from Supabase upsert.")
        return data  # type: ignore[return-value]

    def list_for_user(self, *, user_id: str, limit: int = 100) -> list[PersonRow]:
        resp = (
            self._client.table("people")
            .select("*")
            .eq("user_id", user_id)
            .order("fetched_at", desc=True)
            .limit(limit)
            .execute()
        )
        return expect_list(resp)  # type: ignore[return-value]
