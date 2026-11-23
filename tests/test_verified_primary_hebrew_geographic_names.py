"""Three historically named Hebrew geographic entities have exact original witnesses."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "WestGate": (["13026016"], [["o130260160051", "o130260160061"]]),
    "Gebal.2": (["19083008"], [["o190830080011"]]),
    "Nimrod": (["33005005"], [["o330050050071", "o330050050081"]]),
}

class PrimaryHebrewToponymTests(unittest.TestCase):
    def test_verified_compound_name_exact_tokens_not_guessed(self):
        for name, (refs, words) in CASES.items():
            with self.subTest(name=name):
                o = json.loads((ROOT / "data" / "entities" / "places" /
                                (name + ".json")).read_text(encoding="utf-8"))
                self.assertEqual(o["references"], refs)
                self.assertEqual(o["explicit_instances"], {"wlc": words})
                self.assertTrue(set(refs).issubset(o["key_references"]))
                rows = [e for e in o["bsi"]["editorial_field_changes"]
                        if e["action"] == "restore_direct_primary_hebrew_place_name"]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["added_original_word_groups"], {"wlc": words})
                self.assertEqual(rows[0]["added_reference_values"], {"references": refs})
                self.assertTrue(rows[0]["evidence"] and rows[0]["reason"])
                self.assertEqual(len(o["bsi"]["source_sha256"]), 64)

if __name__ == "__main__":
    unittest.main()
