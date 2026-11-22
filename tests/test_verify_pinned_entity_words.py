"""Pinned original-language word source inventories are independently enforced."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_pinned_word_audit",
    ROOT / "scripts" / "verify_pinned_entity_words.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PinnedEntityWordTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data = Path(tmp.name)
        (self.data / "entities" / "people").mkdir(parents=True)
        self.lock = {"source_editions": {
            "wlc": {"edition": "Clear-Bible/macula-hebrew@pinned",
                    "word_id_prefix": "o", "word_id_digits": 12},
            "sblgnt": {"edition": "Clear-Bible/macula-greek@pinned",
                       "word_id_prefix": "n", "word_id_digits": 11},
        }}
        (self.data / "source.lock.json").write_text(json.dumps(self.lock))
        self.exception = {"corpus": "wlc",
                          "source_edition": self.lock["source_editions"]["wlc"]["edition"],
                          "word_ids": []}
        self.save()
        self.row = {"id": "person:A", "bsi": {"source_id": "person:A"},
                    "explicit_instances": {
                        "wlc": [["o010010010011"]],
                        "SBLGNT": [["n40001001001"]]},
                    "pronominal_referents": {}, "subject_referents": {}}
        self.path = self.data / "entities" / "people" / "A.json"
        self.save_row()
        self.inventories = {
            "wlc": {"o010010010011"},
            "sblgnt": {"n40001001001"},
        }

    def save(self):
        (self.data / "source-unattested-words.json").write_text(
            json.dumps(self.exception))

    def save_row(self):
        self.path.write_text(json.dumps(self.row))

    def test_current_corpora_allow_only_attested_words(self):
        result = mod.audit(self.data, self.inventories)
        self.assertEqual(result["unexpected_missing_words"], [])
        self.assertEqual(result["observed_distinct_words"],
                         {"sblgnt": 1, "wlc": 1})
        self.assertEqual(result["source_annotation_claims"],
                         {"sblgnt:explicit_instances": 1,
                          "wlc:explicit_instances": 1})

    def test_missing_word_is_reported_without_auto_repair(self):
        self.row["explicit_instances"]["SBLGNT"] = [["n40001001002"]]
        self.save_row()
        result = mod.audit(self.data, self.inventories)
        self.assertEqual(result["unexpected_missing_words"],
                         [{"source_id": "person:A", "field": "explicit_instances",
                           "corpus": "sblgnt", "word": "n40001001002",
                           "reason": "absent_from_exact_pinned_source"}])

    def test_known_unauthenticated_original_word_is_subject_only(self):
        missing = "o010010010021"
        self.exception["word_ids"] = [missing]
        self.save()
        self.row["subject_referents"] = {"wlc": [[missing]]}
        self.save_row()
        result = mod.audit(self.data, self.inventories)
        self.assertEqual(result["unexpected_missing_words"], [])
        self.assertEqual(result["documented_source_word_absences"], 1)
        self.row["explicit_instances"]["wlc"] = [[missing]]
        self.save_row()
        result = mod.audit(self.data, self.inventories)
        self.assertTrue(result["invalid_exception_usage"])

    def test_lookalike_numbers_are_not_valid_source_identifiers(self):
        self.row["explicit_instances"]["wlc"] = [["o٠10010010011"]]
        self.save_row()
        self.assertEqual(mod.audit(self.data, self.inventories)
                         ["unexpected_missing_words"][0]["reason"],
                         "invalid_source_word_shape")

    def test_source_exception_list_is_not_a_blanket_waiver(self):
        self.exception["word_ids"] = ["o010010010011"]
        self.save()
        with self.assertRaisesRegex(ValueError, "actually_present"):
            mod.audit(self.data, self.inventories)

    def test_tsv_column_missing_or_duplicate_ids_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "words.tsv"
            p.write_text("wrong\tvalue\nx\ty\n")
            with self.assertRaisesRegex(ValueError, "xml:id"):
                mod.tsv_word_inventory(p)
            p.write_text("xml:id\ttoken\no010010010011\ta\no010010010011\tb\n")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                mod.tsv_word_inventory(p)
            p.write_text("xml:id\ttoken\no010010010011\ta\n")
            self.assertEqual(mod.tsv_word_inventory(p), {"o010010010011"})


if __name__ == "__main__":
    unittest.main()
