"""Known unrelated key-verse and cross-category alias errors remain corrected."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(kind,name):
    return json.loads((ROOT/"data"/"entities"/kind/(name+".json")).read_text(encoding="utf-8"))

class FalseReferenceRepairsTests(unittest.TestCase):
    def test_stater_is_a_coin_not_athens(self):
        coin=read("realia","Stater")
        self.assertEqual(coin["references"],["40017027"])
        self.assertEqual(coin["key_references"],["40017027"])
        self.assertNotIn("Athens",coin["localizations"]["eng"].get("alternate_labels",[]))
        self.assertEqual(coin["explicit_instances"]["SBLGNT"],[["n40017027023"]])
        receipt=coin["bsi"]["editorial_field_changes"][-1]
        self.assertEqual(receipt["removed_reference_values"],
                         {"key_references":["44017016","44018001"]})
        self.assertEqual(receipt["removed_localization_values"],
                         {"eng":{"alternate_labels":["Athens"]}})

    def test_roman_arabia_petraea_not_in_pauls_early_galatians(self):
        roman=read("places","Arabia.2")
        original=read("places","Arabia")
        self.assertEqual(roman["references"],[])
        self.assertEqual(roman["key_references"],[])
        self.assertFalse(roman["mentioned_in_bible"])
        self.assertTrue(roman["non_biblical"])
        self.assertEqual(roman["explicit_instances"],{})
        self.assertTrue(all(v in original["references"]
                            for v in ("48001017","48004025")))
        receipt=roman["bsi"]["editorial_field_changes"][-1]
        self.assertEqual(receipt["removed_reference_values"],
                         {"key_references":["48001017","48004025"]})
        self.assertEqual(receipt["replaced_field_values"],
                         {"mentioned_in_bible":{"from":True,"to":False},
                          "non_biblical":{"from":False,"to":True}})
        self.assertEqual(len(roman["bsi"]["source_sha256"]),64)

if __name__=="__main__":
    unittest.main()
