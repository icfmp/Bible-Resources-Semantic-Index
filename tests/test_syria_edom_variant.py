"""Regression for the reviewed Syria/Edom textual variant distinction."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SyriaEdomEditorialTests(unittest.TestCase):
    def test_textual_variant_is_not_a_geographic_synonym(self):
        record = json.loads((ROOT / "data/entities/places/Syria.json").read_text(encoding="utf-8"))
        self.assertEqual(record["id"], "place:Syria")
        self.assertEqual(record["type"], "place")
        self.assertNotIn("Edom", record["localizations"]["eng"].get("alternate_labels", []))
        decisions = record["bsi"]["editorial_field_changes"]
        matches = [x for x in decisions if x.get("action") == "remove_inherited_textual_variant_as_geographic_alias"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["removed_localization_values"]["eng"]["alternate_labels"], ["Edom"])
        self.assertIn("2 Samuel 8:12", " ".join(matches[0]["evidence"]))
        self.assertIn("1 Chronicles 18:11", " ".join(matches[0]["evidence"]))
        self.assertEqual(record["bsi"]["source_id"], "place:Syria")
        self.assertEqual(len(record["explicit_instances"]["wlc"]), 3)


if __name__ == "__main__":
    unittest.main()
