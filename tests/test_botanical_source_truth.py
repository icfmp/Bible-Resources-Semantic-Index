"""The original source distinguishes direct fruit term from disputed plant species."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def flora(name):
    return json.loads((ROOT/"data"/"entities"/"flora"/(name+".json")).read_text(encoding="utf-8"))
class BotanicalSourceTruthTests(unittest.TestCase):
    def test_joel_tree_is_attested_without_invented_species(self):
        row=flora("AppleTree")
        self.assertIn("29001012",row["references"])
        self.assertIn(["o290010120082"],row["explicit_instances"]["wlc"])
        receipts=[x for x in row["bsi"]["editorial_field_changes"]
                  if x["action"]=="restore_source_attested_apple_tree_word"]
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]["added_reference_values"],
                         {"references":["29001012"]})
    def test_dove_dung_is_not_proven_star_of_bethlehem_species(self):
        row=flora("StarOfBethlehem")
        self.assertEqual(row["references"],[])
        self.assertEqual(row["key_references"],[])
        self.assertEqual(row["explicit_instances"],{})
        self.assertTrue(row["non_biblical"])
        self.assertNotIn("Dove's Dung",row["localizations"]["eng"].get("alternate_labels",[]))
        receipts=[x for x in row["bsi"]["editorial_field_changes"]
                  if x["action"]=="remove_unproved_exact_botanical_species_identity"]
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]["removed_reference_values"],
                         {"key_references":["12006025"]})
        self.assertTrue(receipts[0]["evidence"])
        self.assertEqual(len(row["bsi"]["source_sha256"]),64)
if __name__=="__main__":
    unittest.main()
