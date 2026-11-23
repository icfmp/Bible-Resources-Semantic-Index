"""Pinned source dispositions for a substantial second batch.

Only complete original-language phrases are promoted; contextual homonyms
and falsely species-specific terms remain excluded or key-only.
"""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ANCHORS = {
    "places/Israel": ("wlc", [
        ["o260110170211", "o260110170221"],
        ["o260200380111", "o260200380121"],
        ["o260200420081", "o260200420091"],
        ["o260370120211", "o260370120221"]]),
    "places/Aram-naharaim": ("wlc", [
        ["o070030080101", "o070030080111"],
        ["o010240100151", "o010240100161"]]),
    "places/SinaiWilderness": ("SBLGNT", [
        ["n44007030009", "n44007030011", "n44007030012"]]),
    "places/Babylon.2": ("SBLGNT", [["n66017005009"]]),
    "fauna/Viper": ("SBLGNT", [["n40003007016"]]),
    "fauna/Ibex": ("wlc", [["o090240030172"]]),
    "fauna/Bird": ("SBLGNT", [["n40006026004"]]),
    "people/Abednego": ("wlc", [
        ["o270010060082"], ["o270010190102"]]),
}

def record(kind, name):
    return json.loads((ROOT / "data/entities" / kind / (name + ".json")).read_text("utf-8"))

class OriginalWitnessBatchTests(unittest.TestCase):
    def test_eight_complete_direct_source_edits(self):
        for path,(corp,groups) in SOURCE_ANCHORS.items():
            with self.subTest(path=path):
                kind,name=path.split("/")
                o=record(kind,name)
                receipts=[x for x in o["bsi"]["editorial_field_changes"]
                          if x["action"]=="restore_independently_pinned_exact_direct_mention"]
                self.assertEqual(len(receipts),1)
                receipt=receipts[0]
                self.assertTrue(receipt["reason"])
                self.assertTrue(receipt["evidence"])
                previous=receipt["replaced_field_values"]["before"]
                self.assertTrue(set(previous["references"]).issubset(o["references"]))
                for group in groups:
                    self.assertIn(group,o["explicit_instances"][corp])
                    self.assertNotIn(group,previous["explicit_instances"].get(corp, []))
                    self.assertEqual(len(set(w[1:9] for w in group)),1)
                    self.assertIn(group[0][1:9],o["references"])
                    self.assertIn(group[0][1:9],o["key_references"])
                self.assertEqual(o["bsi"]["review_status"],"editorially_reviewed")
                self.assertEqual(len(o["bsi"]["source_sha256"]),64)

    def test_false_bird_species_and_carmelite_place_links_absent(self):
        sparrow=record("fauna","Sparrow")
        carmel=record("groups","Carmel")
        bird=record("fauna","Bird")
        self.assertEqual(sparrow["key_references"],["40010029"])
        self.assertIn("01015010",bird["references"])
        self.assertIn("21012004",bird["references"])
        self.assertEqual(carmel["key_references"],[])
        self.assertTrue(carmel["references"])
        for record_ in (sparrow,carmel):
            edit=record_["bsi"]["editorial_field_changes"][-1]
            self.assertEqual(edit["action"],"remove_source_proven_wrong_identity_key")
            self.assertTrue(edit["reason"])
            self.assertTrue(edit["evidence"])
            self.assertNotEqual(edit["replaced_field_values"]["before"],
                                edit["replaced_field_values"]["after"])

    def test_symbolic_babylon_and_land_israel_not_same_as_ambiguous_keys(self):
        babylon=record("places","Babylon.2")
        israel=record("places","Israel")
        self.assertIn("66017005",babylon["references"])
        self.assertNotIn("60005013",babylon["references"])
        self.assertIn("60005013",babylon["key_references"])
        self.assertNotIn("40002019",israel["key_references"])
        self.assertNotIn("40002019",israel["references"])
        self.assertNotIn("Jacob",israel["localizations"]["eng"].get("alternate_labels",[]))
        self.assertEqual(israel["bsi"]["editorial_field_changes"][-1]["action"],
                         "remove_source_proven_wrong_identity_key")

    def test_brood_of_vipers_metaphor_remains_lexical_not_presence_claim(self):
        vipers=record("fauna","Viper")
        ibex=record("fauna","Ibex")
        self.assertIn(["n40003007016"],vipers["explicit_instances"]["SBLGNT"])
        self.assertIn(["o090240030172"],ibex["explicit_instances"]["wlc"])
        self.assertNotIn("07004005",record("places","Israel")["references"])

if __name__=="__main__":
    unittest.main()
