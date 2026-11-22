"""Reviewed real-source identity corrections are reversible and source anchored."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def entity(category, name):
    return json.loads(
        (ROOT / "data" / "entities" / category / (name + ".json"))
        .read_text(encoding="utf-8"))


class SourceIdentityCorrectionTests(unittest.TestCase):
    def test_inferred_husband_identities_quarantined_not_fabricated(self):
        for name in ("HusbandOfMary", "HusbandOfMary.2"):
            self.assertFalse((ROOT / "data" / "entities" / "people" /
                              (name + ".json")).exists())
            held = json.loads(
                (ROOT / "data" / "quarantined" / "people" /
                 (name + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(held["bsi"]["state"], "quarantined")
            self.assertTrue(held["bsi"]["evidence"])
            self.assertTrue(held["bsi"]["source_sha256"])
            self.assertEqual(held["explicit_instances"], {})
        for name in ("Mark", "John.5", "James.4", "Joseph.5", "Joses.3", "Salome"):
            self.assertNotIn("father", entity("people", name))
        self.assertEqual(entity("people", "John.5")["mother"], "person:Mary.5")

    def test_salome_is_not_marys_daughter_in_mark_15(self):
        salome = entity("people", "Salome")
        mary = entity("people", "Mary.2")
        self.assertNotIn("mother", salome)
        self.assertNotIn("person:Salome", mary["offspring"])
        self.assertIn("person:James.4", mary["offspring"])
        self.assertIn("person:Joseph.5", mary["offspring"])
        self.assertTrue(any(
            change["removed_relation_values"] == {"offspring": ["person:Salome"]}
            for change in mary["bsi"]["editorial_field_changes"]))

    def test_ezra_3_9_judah_is_not_double_ascribed_to_neh_8_hodiah(self):
        for name in ("Hodiah.2", "Judah.2"):
            person = entity("people", name)
            self.assertNotIn("15003009", person["references"])
            self.assertNotIn(["o150030090081"],
                             person["explicit_instances"]["wlc"])
            edits = [c for c in person["bsi"]["editorial_field_changes"]
                     if c["action"] == "correct_inherited_unrelated_verse_token_attribution"]
            self.assertEqual(len(edits), 1)
            self.assertEqual(edits[0]["removed_original_word_groups"],
                             {"wlc": [["o150030090081"]]})
            self.assertEqual(person["bsi"]["review_status"], "source_unreviewed")
        self.assertIn(["o150030090081"],
                      entity("people", "Hodaviah.4")["explicit_instances"]["wlc"])
        self.assertIn(["o150030090081"],
                      entity("people", "Judah")["explicit_instances"]["wlc"])

    def test_gospel_demonyms_do_not_erase_original_textual_witnesses(self):
        gadara = entity("places", "Gadara")
        gerasa = entity("places", "Gerasa")
        self.assertEqual(gadara["explicit_instances"]["SBLGNT"],
                         [["n40008028011"]])
        self.assertEqual(gerasa["explicit_instances"]["SBLGNT"],
                         [["n41005001012"], ["n42008026007"], ["n42008037010"]])
        self.assertIn("40008028", gerasa["references"])
        self.assertEqual(gerasa["bsi"]["editorial_field_changes"][-1]
                         ["removed_original_word_groups"],
                         {"SBLGNT": [["n40008028011"]]})

    def test_missing_source_explicit_place_verses_are_fixed_without_fake_word(self):
        for name, verse in (("Heres.2", "07001035"),
                            ("ValleyOfMizpeh", "06011008")):
            place = entity("places", name)
            self.assertIn(verse, place["references"])
            self.assertIn(verse, place["key_references"])
            self.assertFalse(place["explicit_instances"])
            edit = place["bsi"]["editorial_field_changes"][-1]
            self.assertEqual(edit["action"], "add_directly_attested_source_verse")
            self.assertEqual(edit["added_reference_values"]["references"], [verse])


if __name__ == "__main__":
    unittest.main()
