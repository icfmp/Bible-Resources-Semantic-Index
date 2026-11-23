"""Review exact source-pinned Hebrew expressions, without inventing geographical identities."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def place(name):
    return json.loads((ROOT / "data" / "entities" / "places" / (name + ".json")).read_text(encoding="utf-8"))

class AttestedTopographicPhrases(unittest.TestCase):
    WITNESSES = {
        "TowerOfShechem": [
            ["o070090460041","o070090460051"], ["o070090470071","o070090470081"],
            ["o070090490221","o070090490231"]],
        "UpperPool": [
            ["o120180170272","o120180170282"],["o230070030162","o230070030172"],
            ["o230360020162","o230360020172"]],
        "ValleyOfDecision": [
            ["o290040140032","o290040140042"],["o290040140092","o290040140102"]],
        "ValleyOfGerar": [["o010260170052","o010260170061"]],
        "WatersOfJericho": [["o060160010072","o060160010081"]],
        "WildernessOfMaon": [
            ["o090230240082","o090230240091"],["o090230250102","o090230250111"],
            ["o090230250171","o090230250181"]],
        "WildernessOfParan": [
            ["o010210210022","o010210210031"],["o040130260131","o040130260141"],
            ["o090250010151","o090250010161"]],
        "WayOfTheRedSea": [
            ["o040140250101","o040140250111","o040140250121"],
            ["o050010400061","o050010400071","o050010400081"]],
        "UpperGulloth": [
            ["o060150190161","o060150190171"],["o070010150181","o070010150191"]],
        "Tabbur-erez": [["o070090370101","o070090370111","o070090370112"]],
        "TheLordWillProvide": [["o010220140061","o010220140071"]],
    }

    def test_every_added_original_phrase_keeps_exact_pinned_word_groups(self):
        for name, groups in self.WITNESSES.items():
            with self.subTest(place=name):
                item=place(name)
                self.assertEqual(item["explicit_instances"], {"wlc": groups})
                verses=sorted(set(word[1:9] for group in groups for word in group))
                self.assertEqual(item["references"], verses)
                self.assertTrue(set(verses).issubset(set(item["key_references"])))
                self.assertEqual(item["bsi"]["review_status"],"editorially_reviewed")
                self.assertEqual(len(item["bsi"]["source_sha256"]),64)
                receipt=item["bsi"]["editorial_field_changes"][-1]
                self.assertEqual(receipt["action"],"restore_exact_attested_topographic_original_phrase")
                self.assertTrue(receipt["reason"])
                self.assertTrue(receipt["evidence"])
                self.assertEqual(receipt["replaced_field_values"]["before"]["references"],[])
                self.assertEqual(receipt["replaced_field_values"]["after"]["references"],verses)

    def test_tabbur_center_of_land_is_not_a_proven_gerizim_alias(self):
        tabbur=place("Tabbur-erez")
        gerizim=place("GerizimMount")
        self.assertNotIn("referred_to_as",tabbur)
        self.assertNotIn("referred_to_as",gerizim)
        self.assertNotIn("Mount Gerizim",tabbur["localizations"]["eng"].get("alternate_labels",[]))
        self.assertIn("07009037",gerizim["key_references"])
        self.assertNotIn("07009037",gerizim["references"])
        self.assertEqual(gerizim["bsi"]["editorial_field_changes"][-1]["action"],
                         "remove_unproven_gerizim_tabbur_equivalence")

    def test_repeated_original_phrases_remain_distinct_within_a_verse(self):
        joel=place("ValleyOfDecision")
        maon=place("WildernessOfMaon")
        self.assertEqual(len(joel["explicit_instances"]["wlc"]),2)
        self.assertEqual(joel["references"],["29004014"])
        self.assertEqual(len([g for g in maon["explicit_instances"]["wlc"]
                              if g[0].startswith("o09023025")]),2)

if __name__ == "__main__":
    unittest.main()
