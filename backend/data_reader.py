"""Читает данные из JSON-файла и возвращает список записей."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_data(path: str | Path) -> list[dict[str, Any]]:
    """
    Загружает JSON. Ожидается массив объектов в корне файла.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Корень JSON должен быть массивом")
    return data
