"""Tribal Ramah identities are source-distinct, never a name-only merge."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def place(name):
    return json.loads((ROOT/"data"/"entities"/"places"/(name+".json")).read_text(encoding="utf-8"))

class DistinctRamahIdentitiesTests(unittest.TestCase):
    def test_asher_naphtali_benjamin_original_words_remain_separate(self):
        asher=place("Ramah.6")
        naphtali=place("Ramah.3")
        benjamin=place("Ramah.4")
        samuel=place("Ramah")
        self.assertEqual(asher["references"],["06019029"])
        self.assertEqual(asher["explicit_instances"]["wlc"],[["o060190290032"]])
        self.assertEqual(naphtali["references"],["06019036"])
        self.assertEqual(naphtali["explicit_instances"]["wlc"],[["o060190360023"]])
        self.assertEqual(benjamin["references"],
                         ["06018025","24031015","40002018"])
        self.assertEqual(benjamin["explicit_instances"],{
            "wlc":[["o060180250023"],["o240310150052"]],
            "SBLGNT":[["n40002018003"]],
        })
        self.assertNotIn("24031015",samuel["key_references"])
        self.assertNotIn("40002018",samuel["key_references"])
        self.assertIn("09001001",samuel["references"])
        self.assertIn("07004005",benjamin["key_references"])
        self.assertNotIn("07004005",benjamin["references"])
        for name in ("Ramah.3","Ramah.4","Ramah"):
            record=place(name)
            receipts=[c for c in record["bsi"]["editorial_field_changes"]
                      if c["action"]=="resolve_cross_tribal_ramah_source_token_misassignment"]
            self.assertEqual(len(receipts),1)
            self.assertTrue(receipts[0]["reason"])
            self.assertTrue(receipts[0]["evidence"])
            self.assertEqual(len(record["bsi"]["source_sha256"]),64)

if __name__=="__main__":
    unittest.main()
