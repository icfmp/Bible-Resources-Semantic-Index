"""Protect original-source Javan ancestor / later Greek people disambiguation."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "entities"

def entity(kind: str, name: str) -> dict:
    return json.loads((DATA / kind / (name + ".json")).read_text(encoding="utf-8"))

class JavanGreekSourceIdentityTests(unittest.TestCase):
    def test_javan_is_ancestor_not_ethnic_greeks(self):
        ancestor = entity("people", "Javan")
        people = entity("groups", "Greek")
        expected = {"o010100020062", "o010100040021",
                    "o130010050062", "o130010070021"}
        direct = {w for groups in ancestor["explicit_instances"].values()
                  for group in groups for w in group}
        self.assertEqual(direct, expected)
        self.assertNotIn("SBLGNT", ancestor["explicit_instances"])
        self.assertEqual(ancestor["references"],
                         ["01010002", "01010004", "13001005", "13001007"])
        self.assertNotIn("27008021", ancestor["key_references"])
        self.assertFalse(ancestor["pronominal_referents"])
        self.assertFalse(ancestor["subject_referents"])
        self.assertNotIn("group:Greek", ancestor.get("referred_to_as", []))
        self.assertFalse(ancestor["localizations"]["eng"].get("alternate_labels"))
        self.assertEqual(people["group_origin"], "person:Javan")
        self.assertEqual(people["bsi"]["canonical_id"], "group:Greek")
        greek = {w for groups in people["explicit_instances"].values()
                 for group in groups for w in group}
        self.assertIn("o290040060072", greek)
        self.assertIn("n43012020003", greek)
        self.assertTrue(all(w.startswith("n") or w == "o290040060072"
                            for w in greek))
        self.assertTrue(direct.isdisjoint(greek))
        self.assertNotEqual(ancestor["bsi"]["source_sha256"],
                            people["bsi"]["source_sha256"])
        receipts = [x for x in ancestor["bsi"]["editorial_field_changes"]
                    if x["action"] == "separate_javan_ancestor_from_greek_ethnonym"]
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]
        self.assertTrue(receipt["reason"] and receipt["evidence"])
        before, after = (receipt["replaced_field_values"][v] for v in ("before","after"))
        self.assertIn("27008021", before["key_references"])
        self.assertNotIn("27008021", after["key_references"])
        self.assertIn("SBLGNT", before["explicit_instances"])
        self.assertNotIn("SBLGNT", after["explicit_instances"])
        self.assertEqual(after["explicit_instances"], ancestor["explicit_instances"])
        self.assertEqual(after["references"], ancestor["references"])

if __name__ == "__main__":
    unittest.main()
