"""Named temple, valley and water constructions require actual Hebrew words."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
    "CityOfPalms.2":(["07001016"],[["o070010160062","o070010160071","o070010160072"]]),
    "Kir-hareseth":(["12003025"],[["o120030250221"]]),
    "JordanValley":(["01013010"],[["o010130100081","o010130100091","o010130100092"]]),
    "MostHolyPlace.1":(["02026033","02026034"],[
       ["o020260330191","o020260330201","o020260330202"],
       ["o020260340072","o020260340081","o020260340082"]]),
    "LowerPool":(["23022009"],[["o230220090112","o230220090121","o230220090122"]]),
}
class UrbanWaterGeographyTests(unittest.TestCase):
    def test_original_named_places_retain_exact_phrase_and_source_receipt(self):
        for name,(refs,words) in EXPECTED.items():
            with self.subTest(name=name):
                x=json.loads((ROOT/"data"/"entities"/"places"/(name+".json"))
                             .read_text(encoding="utf-8"))
                self.assertEqual(x["references"],refs)
                self.assertEqual(x["explicit_instances"],{"wlc":words})
                self.assertTrue(set(refs).issubset(x["key_references"]))
                receipt=[e for e in x["bsi"]["editorial_field_changes"]
                         if e["action"]=="restore_exact_heb_source_urban_geography"]
                self.assertEqual(len(receipt),1)
                self.assertEqual(receipt[0]["added_reference_values"],{"references":refs})
                self.assertEqual(receipt[0]["added_original_word_groups"],{"wlc":words})
                self.assertTrue(receipt[0]["reason"] and receipt[0]["evidence"])
                self.assertEqual(len(x["bsi"]["source_sha256"]),64)
        j=json.loads((ROOT/"data"/"entities"/"places"/"JordanValley.json")
                     .read_text(encoding="utf-8"))
        self.assertNotIn("01019017",j["references"])
        self.assertIn("01019017",j["key_references"])
if __name__=="__main__":
    unittest.main()
