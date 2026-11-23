"""Protect source-only named toponyms from homonymous place promotion."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def place(n):
    return json.loads((ROOT/"data"/"entities"/"places"/(n+".json")).read_text(encoding="utf-8"))
class ExplicitPlaceWitnessTest(unittest.TestCase):
    def test_baalah_negev_does_not_claim_northern_boundary(self):
        row=place("Baalah")
        self.assertEqual(row["references"],["06015029"])
        self.assertNotIn("06015011",row["key_references"])
        self.assertEqual(row["explicit_instances"]["wlc"],[["o060150290011"]])
        edits=[e for e in row["bsi"]["editorial_field_changes"]
               if e["action"]=="withhold_cross_site_geographical_key"]
        self.assertEqual(len(edits),1)
    def test_three_exact_other_place_name_witnesses(self):
        expected={
            "ZionMount":[("10005007","o100050070051"),
                         ("11008001","o110080010271"),
                         ("14005002","o140050020251"),
                         ("19002006","o190020060051")],
            "Almon":[("13006045","o130060450081")],
            "Gedor.3":[("13004018","o130040180071")],
        }
        for name,pairs in expected.items():
            with self.subTest(name=name):
                row=place(name)
                for verse,word in pairs:
                    self.assertIn(verse,row["references"])
                    self.assertIn(verse,row["key_references"])
                    self.assertIn([word],row["explicit_instances"]["wlc"])
                receipts=[e for e in row["bsi"]["editorial_field_changes"]
                          if e["action"]=="restore_original_named_place_token"]
                self.assertEqual(len(receipts),1)
                self.assertEqual(receipts[0]["added_reference_values"],
                                 {"references":[v for v,w in pairs]})
                self.assertTrue(receipts[0]["evidence"])
                self.assertEqual(len(row["bsi"]["source_sha256"]),64)
if __name__=="__main__":
    unittest.main()
