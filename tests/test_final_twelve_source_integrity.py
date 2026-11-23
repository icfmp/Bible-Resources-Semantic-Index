"""Regression evidence for the final twelve source-identity adjudications.

Checks independent biblical word identity, cautious geographic attributions and
reversible no-silent-source-change policy, not a count-driven normalizer.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def entity(kind,name):
    return json.loads((DATA/"entities"/kind/(name+".json")).read_text(encoding="utf-8"))

def words(row):
    return {w for groups in row.get("explicit_instances",{}).values()
            for group in groups for w in group}

class FinalTwelveSourceIntegrityTests(unittest.TestCase):
    def test_ekron_baal_and_nt_beelzebul_not_misidentified(self):
        nt=entity("deities","Beelzebub")
        baal=entity("deities","Baal")
        self.assertEqual(nt["key_references"],["41003022"])
        self.assertEqual(nt["bsi"]["canonical_id"],"deity:Satan")
        self.assertNotIn("12001002",nt["key_references"])
        self.assertNotIn("12001016",nt["key_references"])
        self.assertIn("n41003022010",words(nt))
        for verse in ("12001002","12001016"):
            self.assertIn(verse,baal["key_references"])
            self.assertIn(verse,baal["references"])
        for group in (["o120010020152","o120010020161"],
                      ["o120010160112","o120010160121"]):
            self.assertIn(group,baal["explicit_instances"]["wlc"])
        self.assertNotEqual(nt["bsi"]["source_sha256"],baal["bsi"]["source_sha256"])
        self.assertEqual(nt["bsi"]["source_id"],"deity:Beelzebub")
        self.assertEqual(baal["bsi"]["source_id"],"deity:Baal")
        self.assertNotIn("deity:Satan",baal.get("referred_to_as",[]))

    def test_ai_related_names_have_real_direct_wlc_tokens(self):
        ai=entity("places","Ai")
        aiath=entity("places","Aiath")
        aija=entity("places","Aija")
        self.assertEqual(ai["bsi"]["canonical_id"],"place:Ai")
        self.assertEqual(aiath["bsi"]["canonical_id"],"place:Ai")
        self.assertEqual(aija["bsi"]["canonical_id"],"place:Ai")
        self.assertIn("o130070280141",words(ai))
        self.assertIn("o130070280141",words(aiath))
        self.assertIn("o160110310052",words(aiath))
        self.assertIn("o230100280031",words(aiath))
        self.assertIn("13007028",ai["references"])
        self.assertIn("13007028",aiath["references"])
        self.assertIn("16011031",aiath["references"])

    def test_imagined_towns_not_asserted_as_biblical_cities(self):
        for name,verse in (("Misgab.1","24048001"),("Ramah.8","09022006")):
            with self.subTest(name=name):
                town=entity("places",name)
                self.assertFalse(town["mentioned_in_bible"])
                self.assertTrue(town["non_biblical"])
                self.assertEqual(town["key_references"],[])
                self.assertEqual(town["references"],[])
                self.assertFalse(words(town))
                receipts=[c for c in town["bsi"]["editorial_field_changes"]
                          if c["action"]=="resolve_final_twelve_source_identity"]
                self.assertEqual(len(receipts),1)
                r=receipts[0]["replaced_field_values"]
                self.assertIn(verse,r["before"]["key_references"])
                self.assertNotIn(verse,r["after"]["key_references"])
                self.assertTrue(receipts[0]["evidence"])
        self.assertFalse(entity("places","Ramah.8").get("possibly_same_as",[]))

    def test_botanical_interpretation_is_not_species_fact(self):
        jun=entity("flora","JuniperTree")
        pine=entity("flora","PineTree")
        self.assertIn("proposed",jun["localizations"]["eng"]["preferred_label"])
        self.assertIn("proposed",pine["localizations"]["eng"]["preferred_label"])
        self.assertIn("03014004",jun["key_references"])
        self.assertIn("04019006",jun["key_references"])
        self.assertNotIn("23044014",pine["key_references"])
        self.assertIn("11006023",pine["key_references"])
        self.assertNotIn("Cedar",pine["localizations"]["eng"]["alternate_labels"])
        for item in (jun,pine):
            r=[x for x in item["bsi"]["editorial_field_changes"]
               if x["action"]=="resolve_final_twelve_source_identity"]
            self.assertEqual(len(r),1)
            self.assertTrue(r[0]["reason"] and r[0]["evidence"])

    def test_hebrew_moab_phrase_not_overstated_as_known_city(self):
        row=entity("places","Eglath-shelishiyah.1")
        self.assertEqual(row["key_references"],["23015005","24048034"])
        self.assertIn("possible",row["localizations"]["eng"]["preferred_label"])
        r=next(x for x in row["bsi"]["editorial_field_changes"]
               if x["action"]=="resolve_final_twelve_source_identity")
        self.assertEqual(r["replaced_field_values"]["before"]["preferred_label"],
                         "Eglath-shelishiya")
        self.assertTrue(r["evidence"])

    def test_unmodified_historical_context_not_promoted_into_direct_names(self):
        audit=json.loads((DATA/"source-key-final-128-review.json").read_text(encoding="utf-8"))
        cases={x["source_id"]:x for x in audit["cases"]}
        for sid in ("place:Aphek","place:FoundationGate",
                    "place:GerizimMount","place:Gomer"):
            self.assertEqual(cases[sid]["outcome"],"verified_correct")
            self.assertEqual(cases[sid]["source_proof"]["claimed_relation"],
                             "contextual_or_interpretive_no_new_name_word")
            self.assertFalse(cases[sid].get("required_receipt_action"))
        self.assertNotIn("o070090370101",words(entity("places","GerizimMount")))
        self.assertFalse(words(entity("places","Gomer")))
        self.assertIn("n44023031017",words(entity("places","Antipatris")))

if __name__=="__main__":
    unittest.main()
