"""Explicit people and deity names retain exact WLC sources and distinct meanings."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES={
    "deities/Ashtaroth":[("11011005","o110110050041")],
    "groups/Aramean":[("10008005","o100080050102"),
                      ("10008006","o100080060071")],
    "groups/Archites":[("01010017","o010100170042"),
                       ("13001015","o130010150042")],
    "groups/Jews":[("12016006","o120160060122")],
    "groups/Midian":[("07007025","o070070250211")],
}
class PeopleOriginalWordReviewTests(unittest.TestCase):
    def test_exact_witnesses_and_original_records(self):
        for path,pairs in CASES.items():
            with self.subTest(path=path):
                row=json.loads((ROOT/"data"/"entities"/(path+".json"))
                               .read_text(encoding="utf-8"))
                for verse,word in pairs:
                    self.assertIn(verse,row["references"])
                    self.assertIn(verse,row["key_references"])
                    self.assertIn([word],row["explicit_instances"]["wlc"])
                edits=[x for x in row["bsi"]["editorial_field_changes"]
                       if x["action"]=="restore_original_explicit_ethnonym_or_deity_name"]
                self.assertEqual(len(edits),1)
                self.assertEqual(edits[0]["added_reference_values"],
                                 {"references":[v for v,w in pairs]})
                self.assertEqual(edits[0]["added_original_word_groups"],
                                 {"wlc":[[w] for v,w in pairs]})
                self.assertTrue(edits[0]["reason"] and edits[0]["evidence"])
                self.assertEqual(len(row["bsi"]["source_sha256"]),64)
                self.assertEqual(row["bsi"]["review_status"],"source_unreviewed")
if __name__=="__main__":
    unittest.main()
