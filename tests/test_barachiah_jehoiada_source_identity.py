"""Barachiah in Matthew is not source-proven identical to Jehoiada."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def person(name):
    return json.loads((ROOT/"data"/"entities"/"people"/(name+".json")).read_text(encoding="utf-8"))

class BarachiahJehoiadaSourceTests(unittest.TestCase):
    def test_distinct_original_fathers_not_silently_merged(self):
        matthew=person("Barachiah")
        chronicles=person("Jehoiada.2")
        zechariah=person("Zechariah.12")
        self.assertEqual(matthew["primary_id"],"person:Barachiah")
        self.assertEqual(matthew["bsi"]["canonical_id"],"person:Barachiah")
        self.assertEqual(matthew["references"],["40023035"])
        self.assertEqual(matthew["explicit_instances"]["SBLGNT"],[["n40023035023"]])
        self.assertEqual(matthew["localizations"]["eng"]["preferred_label"],
                         "Barachiah (Matthew 23:35)")
        self.assertNotIn("Jehoiada",matthew["localizations"]["eng"]["alternate_labels"])
        for field in ("offspring","partners","roles","referred_to_as"):
            self.assertNotIn(field,matthew)
        self.assertNotIn("40023035",chronicles["references"])
        self.assertNotIn("40023035",chronicles["key_references"])
        self.assertNotIn("38001001",chronicles["key_references"])
        self.assertNotIn("38001007",chronicles["key_references"])
        self.assertNotIn("SBLGNT",chronicles["explicit_instances"])
        self.assertNotIn("person:Barachiah",chronicles.get("referred_to_as",[]))
        for name in ("Berekiah","Barachiah","Barachias"):
            self.assertNotIn(name,chronicles["localizations"]["eng"].get("alternate_labels",[]))
        self.assertIn("person:Zechariah.12",chronicles["offspring"])
        self.assertEqual(zechariah["father"],"person:Jehoiada.2")
        self.assertIn("40023035",zechariah["references"])
        self.assertEqual(zechariah["explicit_instances"]["SBLGNT"][0],["n40023035021"])
        for p in (matthew,chronicles):
            self.assertEqual(p["bsi"]["review_status"],"source_unreviewed")
            self.assertEqual(len(p["bsi"]["source_sha256"]),64)
            receipts=[x for x in p["bsi"]["editorial_field_changes"]
                      if x["action"]=="separate_unproven_berechiah_jehoiada_source_identity"]
            self.assertEqual(len(receipts),1)
            self.assertTrue(receipts[0]["evidence"] and receipts[0]["reason"])
        self.assertEqual(matthew["bsi"]["source_primary_id"],"person:Jehoiada.2")

if __name__=="__main__":
    unittest.main()
