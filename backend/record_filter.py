"""Отбирает записи из списка по условию."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def select_by_field(
    records: list[dict[str, Any]],
    field: str,
    value: Any,
) -> list[dict[str, Any]]:
    """Возвращает записи, у которых поле `field` равно `value`."""
    return [r for r in records if r.get(field) == value]


def select_where(
    records: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Возвращает записи, для которых `predicate(record)` истинно."""
    return [r for r in records if predicate(r)]
