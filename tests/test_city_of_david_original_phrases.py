"""City of David uses exact compound phrases, not a Jerusalem lemma alone."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class DavidCitySourceTests(unittest.TestCase):
    def test_original_city_name_has_both_word_components(self):
        p=ROOT/"data"/"entities"/"places"/"CityOfDavid.json"
        o=json.loads(p.read_text(encoding="utf-8"))
        original_verses=["10006016","13011007","13015001"]
        original_groups=[["o100060160051","o100060160061"],
                         ["o130110070081","o130110070091"],
                         ["o130150010042","o130150010051"]]
        verses=["10006016","11002010","13011007","13015001"]
        groups=original_groups+[["o110020100062","o110020100071"]]
        self.assertEqual(o["references"],verses)
        self.assertEqual(o["explicit_instances"],{"wlc":groups})
        self.assertTrue(set(verses).issubset(o["key_references"]))
        self.assertIn("10005006",o["key_references"])
        self.assertNotIn("10005006",o["references"])
        receipts=[x for x in o["bsi"]["editorial_field_changes"]
                  if x["action"]=="restore_explicit_city_of_david_compound_name"]
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]["added_reference_values"],{"references":original_verses})
        self.assertEqual(receipts[0]["added_original_word_groups"],{"wlc":original_groups})
        later=[x for x in o["bsi"]["editorial_field_changes"]
               if x["action"]=="restore_city_of_david_first_kings_exact_source_word"]
        self.assertEqual(len(later),1)
        self.assertEqual(later[0]["replaced_field_values"]["before"]["references"],original_verses)
        self.assertEqual(later[0]["replaced_field_values"]["after"]["references"],verses)
        self.assertIn(["o110020100062","o110020100071"],
                      later[0]["replaced_field_values"]["after"]["explicit_instances"]["wlc"])
        self.assertTrue(receipts[0]["evidence"])
        self.assertEqual(len(o["bsi"]["source_sha256"]),64)
if __name__=="__main__":
    unittest.main()
