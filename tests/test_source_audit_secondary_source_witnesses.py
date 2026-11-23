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


class GeographicNamesAndWrongHoronaimTests(unittest.TestCase):
    PHRASES = {
        "BeyondTheJordan": ("SBLGNT", [
            ["n40004025016", "n40004025018"],
            ["n40019001021", "n40019001023"],
            ["n41010001011", "n41010001013"],
            ["n43001028005", "n43001028007"]]),
        "Ir-nahash": ("wlc", [["o130040120111", "o130040120121"]]),
        "Nahor": ("wlc", [["o010240100181", "o010240100191"]]),
        "HolyPlace.2": ("wlc", [["o110080100052"]]),
    }

    def test_four_original_language_location_phrases_attested(self):
        for name, (corpus, groups) in self.PHRASES.items():
            with self.subTest(name=name):
                row = record("places", name)
                self.assertEqual(row["bsi"]["review_status"], "editorially_reviewed")
                self.assertEqual(len(row["bsi"]["source_sha256"]), 64)
                receipts = [receipt for receipt in row["bsi"]["editorial_field_changes"]
                            if receipt["action"] == "restore_direct_pinned_named_location_phrase"]
                self.assertEqual(len(receipts), 1)
                receipt = receipts[0]
                self.assertTrue(receipt["reason"])
                self.assertTrue(receipt["evidence"])
                self.assertEqual(receipt["replaced_field_values"]["after"]["references"],
                                 row["references"])
                old = receipt["replaced_field_values"]["before"]
                self.assertTrue(set(old["references"]).issubset(set(row["references"])))
                for group in groups:
                    self.assertIn(group, row["explicit_instances"][corpus])
                    self.assertNotIn(group, old["explicit_instances"].get(corpus, []))
                    self.assertEqual(len(set(w[1:9] for w in group)), 1)
                    self.assertIn(group[0][1:9], row["references"])
                    self.assertIn(group[0][1:9], row["key_references"])

    def test_holy_place_is_not_automatically_the_inner_sanctuary(self):
        holy = record("places", "HolyPlace.2")
        self.assertNotIn("Inner Sanctuary",
                         holy["localizations"]["eng"].get("alternate_labels", []))
        self.assertIn("11006005", holy["key_references"])
        self.assertNotIn("11006005", holy["references"])
        self.assertIn("11008010", holy["references"])

    def test_absaloms_flight_does_not_invent_another_horonaim(self):
        moab = record("places", "Horonaim")
        spurious = record("places", "Horonaim.2")
        self.assertNotIn("10013034", moab["references"])
        self.assertNotIn("10013034", spurious["key_references"])
        self.assertFalse(spurious["mentioned_in_bible"])
        self.assertTrue(spurious["non_biblical"])
        self.assertEqual(spurious["references"], [])
        self.assertEqual(spurious["explicit_instances"], {})
        self.assertIn("23015005", moab["references"])
        for row, action in [
            (moab, "remove_unrelated_absalom_mountain_verse_from_moab_horonaim"),
            (spurious, "remove_fabricated_horonaim_in_absalom_narrative")
        ]:
            receipt = row["bsi"]["editorial_field_changes"][-1]
            self.assertEqual(receipt["action"], action)
            self.assertTrue(receipt["reason"])
            self.assertTrue(receipt["evidence"])
            self.assertNotEqual(receipt["replaced_field_values"]["before"],
                                receipt["replaced_field_values"]["after"])

if __name__=="__main__":
    unittest.main()
