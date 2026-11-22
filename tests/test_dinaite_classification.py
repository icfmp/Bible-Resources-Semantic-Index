"""Dinaite is a plural group despite uncertain ethnonym-vs-office reading."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DinaiteClassificationTests(unittest.TestCase):
    def test_collective_identity_keeps_original_source_witness(self):
        record = json.loads((ROOT / "data/entities/people/Dinaite.json").read_text(encoding="utf-8"))
        self.assertEqual(record["id"], "group:Dinaite")
        self.assertEqual(record["primary_id"], "group:Dinaite")
        self.assertEqual(record["type"], "group")
        self.assertEqual(record["bsi"]["canonical_id"], "group:Dinaite")
        self.assertNotIn("gender", record)
        self.assertEqual(record["bsi"]["source_id"], "person:Dinaite")
        self.assertEqual(record["references"], ["15004009"])
        self.assertEqual(record["key_references"], ["15004009"])
        self.assertEqual(record["explicit_instances"]["wlc"], [["o150040090091"]])
        self.assertEqual(record["bsi"]["review_status"], "editorially_reviewed")
        edits = [x for x in record["bsi"]["editorial_field_changes"] if x["action"] == "reclassify_inherited_individual_as_collective"]
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]["removed_fields"]["gender"], "male")
        self.assertIn("ethnonym", edits[0]["reason"])


if __name__ == "__main__":
    unittest.main()
