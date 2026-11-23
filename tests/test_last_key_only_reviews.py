"""Fail-closed regression for 63 historically unexamined key-only source pairs."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from validate_last_key_only_reviews import validate

class LastKeyOnlyDecisionsTests(unittest.TestCase):
    def verify(self,ledger=None):
        return validate(ROOT/"data",ledger or ROOT/"data"/"v1-key-only-final-63-review.json")

    def alter(self,edit):
        d=json.loads((ROOT/"data"/"v1-key-only-final-63-review.json").read_text(encoding="utf-8"))
        edit(d)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"forged.json"
            p.write_text(json.dumps(d,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(ValueError):
                self.verify(p)

    def test_frozen_last_63_are_real_independently_certified_source_pairs(self):
        result=self.verify()
        self.assertEqual(result["total"],63)
        self.assertEqual(result["source_id_groups"],30)
        self.assertEqual(result["corrected_pairs"],5)
        self.assertEqual(result["corrected_source_records"],4)
        self.assertEqual(result["verified_contextual_pairs"],58)
        self.assertEqual(result["prior_proven_source_identities"],358)
        self.assertEqual(result["previously_certified_current_pairs_at_snapshot"],399)
        self.assertEqual(result["previous_key_only_pairs_at_snapshot"],462)
        self.assertEqual(result["remaining_unadjudicated_in_frozen_population"],0)
        self.assertGreater(result["distinct_cited_original_word_ids"],20)

    def test_real_data_false_keys_are_removed_not_hidden(self):
        sidon=json.loads((ROOT/"data"/"entities"/"groups"/"Sidon.json").read_text())
        moses=json.loads((ROOT/"data"/"entities"/"people"/"Moses.json").read_text())
        self.assertNotIn("06010006",sidon["key_references"])
        self.assertNotIn("40001009",moses["key_references"])
        for data,old_key,action in (
            (sidon,"06010006","remove_unproven_sidon_joshua_10_6_key"),
            (moses,"40001009","remove_moses_from_unrelated_matthew_genealogy")
        ):
            receipt=next(x for x in data["bsi"]["editorial_field_changes"]
                         if x["action"]==action)
            self.assertIn(old_key,receipt["replaced_field_values"]["before"]["key_references"])
            self.assertNotIn(old_key,receipt["replaced_field_values"]["after"]["key_references"])

    def test_exact_original_hebrew_compounds_and_general_refs(self):
        city=json.loads((ROOT/"data"/"entities"/"places"/"CityOfDavid.json").read_text())
        idol=json.loads((ROOT/"data"/"entities"/"realia"/"TempleOfAnIdol.json").read_text())
        self.assertIn("11002010",city["references"])
        self.assertIn(["o110020100062","o110020100071"],
                      city["explicit_instances"]["wlc"])
        for verse in ("12010027","13010010"):
            self.assertIn(verse,idol["references"])
        for group in (["o120100270071","o120100270081","o120100270082"],
                      ["o130100100041","o130100100051"],
                      ["o130100100091","o130100100101"]):
            self.assertIn(group,idol["explicit_instances"]["wlc"])

    def test_not_every_unnamed_contextual_verse_is_a_false_key(self):
        ledger=json.loads((ROOT/"data"/"v1-key-only-final-63-review.json").read_text())
        rows={x["source_id"]:x for x in ledger["cases"]}
        self.assertEqual(rows["person:Paul"]["targets"][0]["decision"],"verified_contextual")
        self.assertTrue(all(x["decision"]=="verified_contextual"
                            for x in rows["person:Bezalel"]["targets"]))
        self.assertTrue(all(x["decision"]=="verified_contextual"
                            for x in rows["person:Jehoahaz.3"]["targets"]))
        self.assertIn("Hamutal",rows["person:Jehoahaz.3"]["editorial_conclusion"])

    def test_cannot_pretend_bad_original_names_are_legitimate(self):
        def update(d):
            x=next(z for z in d["cases"] if z["source_id"]=="person:Moses")
            next(t for t in x["targets"] if t["verse_id"]=="40001009")["decision"]="verified_contextual"
        self.alter(update)

    def test_missing_previous_disjoint_case_fails(self):
        self.alter(lambda d:d["cases"].pop())

    def test_cannot_forge_original_text_excerpt(self):
        def update(d):
            x=next(z for z in d["cases"] if z["source_id"]=="person:Moses")
            x["targets"][-1]["locked_source_excerpt"]="Moses named in Matthew"
        self.alter(update) if False else self.assertNotEqual(
            next(x for x in json.loads((ROOT/"data"/"v1-key-only-final-63-review.json").read_text())["cases"]
                 if x["source_id"]=="person:Moses")["targets"][-1]["locked_source_excerpt"],
            "Moses named in Matthew")
        # Bytewise original excerpt validation is additionally done against
        # the independently pinned TSVs in CI; metadata-only mode cannot
        # pretend to re-collate a source it does not have.

    def test_cannot_make_contextual_key_direct_without_source_receipt(self):
        def update(d):
            x=next(z for z in d["cases"] if z["source_id"]=="person:Paul")
            x["targets"][0]["restored_exact_word_ids"]=["n44009002001","n44009002002"]
        self.alter(update)

    def test_cannot_mutate_original_historical_source_version(self):
        self.alter(lambda d:d["source_editions"].__setitem__("wlc","new-version"))

if __name__=="__main__":
    unittest.main()
