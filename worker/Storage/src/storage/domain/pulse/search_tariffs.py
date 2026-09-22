from __future__ import annotations

from typing import Any

from storage.core.response import expect_single


class SearchTariffRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    def list_all(self) -> list[dict[str, Any]]:
        resp = self._client.table("search_tariffs").select("*").order("sort_order", desc=False).order("created_at", desc=False).execute()
        data = getattr(resp, "data", None)
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

    def get_default(self) -> dict[str, Any] | None:
        resp = (
            self._client.table("search_tariffs")
            .select("*")
            .order("sort_order", desc=False)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        data = getattr(resp, "data", None)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, dict):
            return data
        return None

    def get_by_id(self, *, tariff_id: str) -> dict[str, Any] | None:
        resp = self._client.table("search_tariffs").select("*").eq("id", tariff_id).maybe_single().execute()
        row = getattr(resp, "data", None)
        return row if isinstance(row, dict) else None

    def resolve(self, *, tariff_id: str | None) -> dict[str, Any] | None:
        if tariff_id:
            row = self.get_by_id(tariff_id=tariff_id)
            if row:
                return row
        return self.get_default()

    def create(
        self,
        *,
        title: str,
        max_scan_count: int,
        target_found_count: int,
        min_relevance_percent: int,
        sort_order: int = 0,
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "max_scan_count": max_scan_count,
            "target_found_count": target_found_count,
            "min_relevance_percent": min_relevance_percent,
            "sort_order": sort_order,
        }
        resp = self._client.table("search_tariffs").insert(payload).execute()
        return expect_single(resp)  # type: ignore[return-value]

    def update(
        self,
        *,
        tariff_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        resp = self._client.table("search_tariffs").update(patch).eq("id", tariff_id).execute()
        return expect_single(resp)  # type: ignore[return-value]

    def delete(self, *, tariff_id: str) -> None:
        self._client.table("search_tariffs").delete().eq("id", tariff_id).execute()

