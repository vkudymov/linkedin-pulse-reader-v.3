from __future__ import annotations

import json
from dataclasses import asdict

from ..types import ReportItem, ReportMeta


def build_json(*, items: list[ReportItem], meta: ReportMeta) -> bytes:
    payload = {
        "meta": asdict(meta),
        "items": [asdict(i) for i in items],
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

