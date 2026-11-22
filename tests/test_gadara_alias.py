"""A demonym textual variant is not a synonym between separate cities."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GadaraAliasTests(unittest.TestCase):
    def test_gerasa_is_not_a_gadara_alias(self):
        a = json.loads((ROOT / "data/entities/places/Gadara.json").read_text(encoding="utf-8"))
        self.assertEqual(a["id"], "place:Gadara")
        self.assertNotIn("Gerasa", a["localizations"]["eng"].get("alternate_labels", []))
        edits = [x for x in a["bsi"]["editorial_field_changes"] if x["action"] == "remove_inherited_cross_city_label"]
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]["removed_localization_values"]["eng"]["alternate_labels"], ["Gerasa"])
        self.assertEqual(a["explicit_instances"]["SBLGNT"], [["n40008028011"]])
        self.assertEqual(a["bsi"]["source_id"], "place:Gadara")
        self.assertIn("place:Gadara", a["primary_id"])


if __name__ == "__main__":
    unittest.main()
