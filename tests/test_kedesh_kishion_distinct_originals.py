"""Kedesh of Judah cannot own Kishion's northern name/coordinates."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def place(name):
    return json.loads((ROOT/"data"/"entities"/"places"/(name+".json")).read_text(encoding="utf-8"))
class DistinctKedeshTribalWitnessTests(unittest.TestCase):
    def test_kedesh_judah_keeps_its_own_exact_joshua_word(self):
        south=place("Kedesh.2")
        north=place("Kishion")
        kedesh_issachar=place("Kedesh.3")
        self.assertEqual(south["bsi"]["canonical_id"],"place:Kedesh.2")
        self.assertEqual(south["primary_id"],"place:Kedesh.2")
        self.assertEqual(south["bsi"]["source_primary_id"],"place:Kishion")
        self.assertEqual(south["references"],["06015023"])
        self.assertEqual(south["explicit_instances"]["wlc"],[["o060150230012"]])
        self.assertNotIn("Kishion",south["localizations"]["eng"]["alternate_labels"])
        self.assertNotIn("referred_to_as",south)
        self.assertNotIn("geocoordinates",south)
        self.assertIn("06019020",north["references"])
        self.assertIn("13006057",north["references"])
        self.assertIn("13006057",kedesh_issachar["references"])
        self.assertNotIn("13006057",south["references"])
        receipts=[x for x in south["bsi"]["editorial_field_changes"]
                  if x["action"]=="split_false_kedesh_judah_kishion_issachar_identification"]
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]["replaced_field_values"]["primary_id"],
                         {"from":"place:Kishion","to":"place:Kedesh.2"})
        self.assertTrue(receipts[0]["removed_source_geocoordinates"])
        self.assertTrue(receipts[0]["evidence"])
        self.assertEqual(len(south["bsi"]["source_sha256"]),64)
if __name__=="__main__":
    unittest.main()
