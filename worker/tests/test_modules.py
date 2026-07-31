"""Тесты для data_reader и record_filter."""

import json
import tempfile
import unittest
from pathlib import Path

from data_reader import read_data
from record_filter import select_by_field, select_where


class TestDataReader(unittest.TestCase):
    def test_reads_array(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump([{"a": 1}, {"a": 2}], f)
            path = f.name
        try:
            rows = read_data(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["a"], 1)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_rejects_non_array_root(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump({"items": []}, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                read_data(path)
        finally:
            Path(path).unlink(missing_ok=True)


class TestRecordFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {"id": 1, "kind": "x", "on": True},
            {"id": 2, "kind": "y", "on": False},
            {"id": 3, "kind": "x", "on": True},
        ]

    def test_select_by_field(self) -> None:
        got = select_by_field(self.records, "kind", "x")
        self.assertEqual(len(got), 2)
        self.assertTrue(all(r["kind"] == "x" for r in got))

    def test_select_where(self) -> None:
        got = select_where(self.records, lambda r: r.get("on") is True)
        self.assertEqual({r["id"] for r in got}, {1, 3})


if __name__ == "__main__":
    unittest.main()
