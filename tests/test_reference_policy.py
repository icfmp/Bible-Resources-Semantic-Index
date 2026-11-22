"""ORG BCV8 source reference shape, with independent key/reference semantics."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_reference_policy", ROOT / "scripts" / "reference_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class NativeReferenceFieldTests(unittest.TestCase):
    def test_independent_reference_lists_preserved(self):
        for path, expected in (
            ("places/ValleyOfMizpeh.json", ([], ["06011008"])),
            ("places/Heres.2.json", ([], [])),
            ("deities/Ashtaroth.json", (
                ["07002013", "07010006", "09007003", "09007004",
                 "09012010", "09031010"],
                ["11011005", "07010006"],
            )),
        ):
            with self.subTest(path=path):
                record = json.loads((ROOT / "data" / "entities" / path)
                                    .read_text(encoding="utf-8"))
                original = copy.deepcopy(record)
                self.assertEqual(
                    (record["references"], record["key_references"]), expected)
                policy.validate_reference_fields(record)
                self.assertEqual(record, original)

    def test_rejects_non_bcv8_and_malformed_collections(self):
        valid = {"references": ["01001001"], "key_references": ["01001002"]}
        for field in ("references", "key_references"):
            for value in ("0100101", "010010001", "Genesis 1:1",
                          "0100100X", 1001001, "０１００１００１"):
                with self.subTest(field=field, value=value):
                    record = copy.deepcopy(valid)
                    record[field] = [value]
                    with self.assertRaisesRegex(ValueError, field):
                        policy.validate_reference_fields(record)
            for invalid in (None, "01001001", {}, ()):
                with self.subTest(field=field, invalid=invalid):
                    record = copy.deepcopy(valid)
                    record[field] = invalid
                    with self.assertRaisesRegex(ValueError, field):
                        policy.validate_reference_fields(record)
            record = copy.deepcopy(valid)
            del record[field]
            with self.assertRaisesRegex(ValueError, field):
                policy.validate_reference_fields(record)

    def test_distinct_key_reference_is_not_promoted_to_occurrence(self):
        record = {
            "references": [],
            "key_references": ["06011008"],
            "explicit_instances": {},
        }
        before = copy.deepcopy(record)
        policy.validate_reference_fields(record)
        self.assertEqual(record, before)

    def test_source_order_and_duplicates_are_preserved_for_editorial_review(self):
        record = {
            "references": ["01001002", "01001001", "01001001"],
            "key_references": ["01001002", "01001002"],
        }
        before = copy.deepcopy(record)
        policy.validate_reference_fields(record)
        self.assertEqual(record, before)


if __name__ == "__main__":
    unittest.main()
