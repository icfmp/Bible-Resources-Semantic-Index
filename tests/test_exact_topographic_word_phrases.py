"""Exact frozen Hebrew compound names; do not confuse context with mention."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
    "Goshen.3":(["06010041","06011016"],
      [["o060100410091","o060100410101"],["o060110160131","o060110160141","o060110160142"]]),
    "LowerGulloth":(["06015019","07001015"],
      [["o060150190191","o060150190201"],["o070010150211","o070010150221"]]),
    "MiddleGate":(["24039003"],
      [["o240390030072","o240390030081","o240390030082"]]),
    "OldPool":(["23022011"],
      [["o230220110062","o230220110071","o230220110072"]]),
    "Harod.1":(["07007001"],
      [["o070070010111","o070070010121"]]),
    "Ramathaim-zophim":(["09001001"],
      [["o090010010052","o090010010061"]]),
}
class HebrewToponymReceiptsTests(unittest.TestCase):
    def test_reviewed_original_phrase_evidence_is_exact(self):
        for name,(refs,words) in EXPECTED.items():
            with self.subTest(name=name):
                o=json.loads((ROOT/"data"/"entities"/"places"/(name+".json"))
                             .read_text(encoding="utf-8"))
                self.assertEqual(o["references"],refs)
                self.assertEqual(o["explicit_instances"],{"wlc":words})
                edits=[x for x in o["bsi"]["editorial_field_changes"]
                       if x["action"]=="restore_exact_frozen_wlc_geographic_compound"]
                self.assertEqual(len(edits),1)
                self.assertEqual(edits[0]["added_original_word_groups"],{"wlc":words})
                self.assertEqual(edits[0]["added_reference_values"],{"references":refs})
                self.assertTrue(edits[0]["reason"] and edits[0]["evidence"])
                self.assertEqual(len(o["bsi"]["source_sha256"]),64)
    def test_rock_of_etam_source_text_not_joshua_15_52(self):
        o=json.loads((ROOT/"data"/"entities"/"places"/"Etam.4.json")
                     .read_text(encoding="utf-8"))
        self.assertEqual(o["references"],["07015008","07015011"])
        self.assertEqual(o["key_references"],["07015008","07015011"])
        self.assertNotIn("06015052",o["key_references"])
        self.assertEqual(o["explicit_instances"],{"wlc":[
            ["o070150080102","o070150080111","o070150080121"],
            ["o070150110071","o070150110081","o070150110091"]]})
        self.assertEqual(o["primary_id"],"place:Etam.4")
        edits=[x for x in o["bsi"]["editorial_field_changes"]
               if x["action"]=="correct_rock_of_etam_to_explicit_samson_site"]
        self.assertEqual(len(edits),1)
        self.assertEqual(edits[0]["removed_reference_values"],
                         {"key_references":["06015052"]})
        self.assertTrue(edits[0]["evidence"])
        self.assertEqual(len(o["bsi"]["source_sha256"]),64)
if __name__=="__main__":
    unittest.main()
