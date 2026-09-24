from __future__ import annotations

from dataclasses import asdict
from xml.etree import ElementTree as ET

from ..types import ReportItem, ReportMeta


def _set_text(parent: ET.Element, tag: str, value: object | None) -> None:
    el = ET.SubElement(parent, tag)
    el.text = "" if value is None else str(value)


def build_xml(*, items: list[ReportItem], meta: ReportMeta) -> bytes:
    root = ET.Element("search_report")
    meta_el = ET.SubElement(root, "meta")
    for k, v in asdict(meta).items():
        _set_text(meta_el, k, v)

    items_el = ET.SubElement(root, "items")
    for it in items:
        it_el = ET.SubElement(items_el, "item")
        d = asdict(it)
        for k, v in d.items():
            if k in ("matched_requirements", "missing_requirements", "red_flags"):
                arr_el = ET.SubElement(it_el, k)
                for x in (v or []):
                    _set_text(arr_el, "value", x)
                continue
            if k == "extra" and isinstance(v, dict):
                extra_el = ET.SubElement(it_el, "extra")
                for ek, ev in v.items():
                    e_el = ET.SubElement(extra_el, "field", name=str(ek))
                    e_el.text = "" if ev is None else str(ev)
                continue
            _set_text(it_el, k, v)

    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml + b"\n"

