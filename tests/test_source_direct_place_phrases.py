"""Reviewed original-language direct places must retain individual source receipts."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "JacobsWell": (
        ["43004006"],
        {"SBLGNT": [["n43004006004", "n43004006005", "n43004006006"]]},
        ["43004005"],
    ),
    "Machbenah": (
        ["13002049"],
        {"wlc": [["o130020490081"]]},
        ["13002049"],
    ),
}

class SourcePhraseVerificationTests(unittest.TestCase):
    def test_source_exact_word_attestation_and_distinct_key_semantics(self):
        for name, (verses, instances, keys) in CASES.items():
            with self.subTest(name=name):
                o = json.loads((ROOT / "data" / "entities" / "places" /
                                (name + ".json")).read_text(encoding="utf-8"))
                self.assertEqual(o["references"], verses)
                self.assertEqual(o["explicit_instances"], instances)
                self.assertEqual(o["key_references"], keys)
                self.assertEqual(o["bsi"]["review_status"], "source_unreviewed")
                self.assertEqual(len(o["bsi"]["source_sha256"]), 64)
                receipts = [item for item in o["bsi"]["editorial_field_changes"]
                            if item["action"] == "restore_source-attested_direct_place_phrase"]
                self.assertEqual(len(receipts), 1)
                self.assertEqual(receipts[0]["added_original_word_groups"], instances)
                self.assertEqual(receipts[0]["added_reference_values"], {"references": verses})
                self.assertTrue(receipts[0]["evidence"])

if __name__ == "__main__":
    unittest.main()
