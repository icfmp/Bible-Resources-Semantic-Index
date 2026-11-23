"""No unsupported canonical Bible witness for historical/apocryphal towns."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UnattestedCanonicalPlaceTests(unittest.TestCase):
    def test_three_originally_unanchored_towns_not_claimed_as_biblical(self):
        for n in ("Daphne","HeracleopolisMagna","Raphia"):
            with self.subTest(n=n):
                o=json.loads((ROOT/"data"/"entities"/"places"/(n+".json")).read_text(encoding="utf-8"))
                self.assertEqual(o["references"],[])
                self.assertEqual(o["key_references"],[])
                self.assertEqual(o["explicit_instances"],{})
                self.assertFalse(o["mentioned_in_bible"])
                self.assertTrue(o["non_biblical"])
                change=[x for x in o["bsi"]["editorial_field_changes"]
                        if x["action"]=="correct_no_canonical_bible_attestation_flag"]
                self.assertEqual(len(change),1)
                self.assertEqual(change[0]["replaced_field_values"]["mentioned_in_bible"],
                                 {"from":True,"to":False})
                self.assertTrue(change[0]["evidence"])
                self.assertEqual(len(o["bsi"]["source_sha256"]),64)
        self.assertTrue(json.loads((ROOT/"data"/"entities"/"places"/"Daphne.json")
                        .read_text(encoding="utf-8"))["only_mentioned_in_apocrypha"])
        self.assertTrue(json.loads((ROOT/"data"/"entities"/"places"/"Raphia.json")
                        .read_text(encoding="utf-8"))["only_mentioned_in_apocrypha"])
if __name__=="__main__":
    unittest.main()
