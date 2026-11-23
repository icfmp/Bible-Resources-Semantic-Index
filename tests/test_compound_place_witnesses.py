"""Source-attested compound Hebrew toponyms and locative morphology."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "Beth-aven.2": (["28010005"], {"wlc":[["o280100050021","o280100050031"]]}),
    "Ir-shemesh": (["06019041"], {"wlc":[["o060190410062","o060190410071"]]}),
    "Timnah.1": (["06015010","07014001"], {"wlc":[["o060150100201"],["o070140010031","o070140010032"],["o070140010062"]]}),
}


class CompoundPlaceWordEvidenceTests(unittest.TestCase):
    def test_full_original_word_groups_and_direct_verse_claims(self):
        for name, (verses, groups) in EXPECTED.items():
            with self.subTest(name=name):
                p = ROOT / "data" / "entities" / "places" / (name + ".json")
                record = json.loads(p.read_text(encoding="utf-8"))
                self.assertEqual(record["references"], verses)
                self.assertEqual(record["explicit_instances"], groups)
                self.assertTrue(set(verses).issubset(record["key_references"]))
                self.assertEqual(record["bsi"]["review_status"], "source_unreviewed")
                change = [row for row in record["bsi"]["editorial_field_changes"]
                          if row["action"] == "restore_direct_compound_place_word_witness"]
                self.assertEqual(len(change), 1)
                self.assertEqual(change[0]["added_original_word_groups"], groups)
                self.assertEqual(change[0]["added_reference_values"], {"references": verses})
                self.assertTrue(change[0]["evidence"])
                self.assertEqual(len(record["bsi"]["source_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
