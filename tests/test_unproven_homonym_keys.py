"""Homonymous fathers and towns must not inherit another exact-source key."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def entity(kind,name):
    return json.loads((ROOT/"data"/"entities"/kind/(name+".json")).read_text(encoding="utf-8"))

class DistinctSourceKeyTests(unittest.TestCase):
    def test_two_alphaeus_fathers_are_not_identified_by_name_alone(self):
        james=entity("people","Alphaeus")
        levi=entity("people","Alphaeus.2")
        self.assertNotIn("41002014",james["key_references"])
        self.assertIn("41002014",levi["references"])
        self.assertEqual(levi["explicit_instances"]["SBLGNT"],[["n41002014007"]])
        self.assertIn("40010003",james["references"])

    def test_sauls_bezek_is_not_assumed_adonibezeks_site(self):
        adoni=entity("places","Bezek")
        saul=entity("places","Bezek.2")
        self.assertNotIn("09011008",adoni["key_references"])
        self.assertEqual(adoni["localizations"]["eng"]["preferred_label"],
                         "Bezek (Adoni-bezek)")
        self.assertTrue({"07001004","07001005"}.issubset(adoni["references"]))
        self.assertEqual(saul["references"],["09011008"])
        self.assertEqual(saul["explicit_instances"]["wlc"],[["o090110080022"]])

    def test_rock_of_etam_is_not_automatically_fortified_city(self):
        etam=entity("places","Etam")
        self.assertNotIn("14011006",etam["key_references"])
        self.assertEqual(etam["references"],["07015008","07015011"])
        self.assertEqual(len(etam["explicit_instances"]["wlc"]),2)

    def test_all_withholds_retain_original_source_values(self):
        for kind,name in (("people","Alphaeus"),("places","Bezek"),
                          ("places","Etam")):
            row=entity(kind,name)
            edits=[x for x in row["bsi"]["editorial_field_changes"]
                   if x["action"]=="remove_unproven_cross_entity_key_identity"]
            self.assertEqual(len(edits),1)
            self.assertTrue(edits[0]["removed_reference_values"]["key_references"])
            self.assertTrue(edits[0]["evidence"])
            self.assertEqual(len(row["bsi"]["source_sha256"]),64)

if __name__=="__main__":
    unittest.main()
