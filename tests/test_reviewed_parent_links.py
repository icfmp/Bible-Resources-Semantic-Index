"""Reviewed changes to explicit parent links preserve ACAI source provenance."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def entity(name: str) -> dict:
    return json.loads((ROOT / "data" / "entities" / "people" / f"{name}.json")
                      .read_text(encoding="utf-8"))


class ReviewedFamilyRelationshipTests(unittest.TestCase):
    def test_lot_wife_is_not_grandsons_direct_mother(self):
        wife = entity("WifeOfLot")
        self.assertEqual(wife["offspring"],
                         ["person:Daughter1OfLot", "person:Daughter2OfLot"])
        self.assertEqual(entity("Moab")["mother"], "person:Daughter1OfLot")
        self.assertEqual(entity("Ben-ammi")["mother"], "person:Daughter2OfLot")
        self.assertEqual(wife["bsi"]["source_sha256"],
                         "d6afd3c104a7f1acf498698b351a0d5503de58b1cf8278784cb3cadd20461d82")
        self.assertEqual(wife["bsi"]["review_status"], "source_unreviewed")
        change = wife["bsi"]["editorial_field_changes"][0]
        self.assertEqual(set(change["removed_relation_values"]["offspring"]),
                         {"person:Moab", "person:Ben-ammi"})
        self.assertIn("19:36-38", " ".join(change["evidence"]))

    def test_eliasaph_names_deuel_not_jethro(self):
        eliasaph = entity("Eliasaph")
        self.assertEqual(eliasaph["father"], "person:Deuel")
        self.assertEqual(entity("Reuel")["bsi"]["canonical_id"], "person:Deuel")
        self.assertIn("person:Eliasaph", entity("Deuel")["offspring"])
        self.assertIn("person:Eliasaph", entity("Reuel")["offspring"])
        self.assertEqual(eliasaph["bsi"]["source_sha256"],
                         "db557df80139e5753220933b5452317bbff9fea8526d246c5ddc9e6209e12413")
        self.assertEqual(eliasaph["bsi"]["review_status"], "source_unreviewed")
        change = eliasaph["bsi"]["editorial_field_changes"][0]
        self.assertEqual(change["replaced_relation_values"]["father"],
                         {"from": "person:Jethro", "to": "person:Deuel"})
        self.assertIn("Numbers 1:14", " ".join(change["evidence"]))

    def test_unattested_husband_links_are_withheld_without_erasing_mary_mark(self):
        self.assertNotIn("father", entity("Mark"))
        self.assertEqual(entity("Mark")["mother"], "person:Mary.5")
        self.assertIn("person:Mark", entity("Mary.5")["offspring"])
        for name in ("HusbandOfMary", "HusbandOfMary.2"):
            placeholder = json.loads((ROOT / "data" / "quarantined" / "people" /
                                      (name + ".json")).read_text(encoding="utf-8"))
            self.assertNotIn("offspring", placeholder)
            self.assertNotIn("partners", placeholder)
            self.assertEqual(placeholder["bsi"]["review_status"], "source_unreviewed")
            self.assertEqual(placeholder["explicit_instances"], {})
            self.assertEqual(placeholder["bsi"]["state"], "quarantined")
            self.assertFalse((ROOT / "data" / "entities" / "people" /
                              (name + ".json")).exists())
        for name in ("Mary.2", "Mary.5"):
            self.assertNotIn("partners", entity(name))
        self.assertEqual(entity("Mary.2")["bsi"]["identity_hint"]["qualifier"],
                         "mother of James the younger and Joses")

    def test_source_ambiguous_maternal_links_are_not_exported_as_facts(self):
        for name in ("Jesher", "Shobab.2", "Ardon"):
            son = entity(name)
            self.assertEqual(son["father"], "person:Caleb.2")
            self.assertNotIn("mother", son)
            self.assertEqual(son["references"], ["13002018"])
            self.assertEqual(son["bsi"]["review_status"], "source_unreviewed")
        self.assertNotIn("offspring", entity("Azubah.2"))
        self.assertEqual(entity("Jerioth")["references"], ["13002018"])

    def test_distinct_zimmah_genealogies_remain_witnesses_not_merged_parent(self):
        self.assertNotIn("father", entity("Zimmah"))
        self.assertNotIn("offspring", entity("Jahath.2"))
        self.assertNotIn("offspring", entity("Shimei.2"))
        self.assertEqual(entity("Zimmah")["references"], ["13006005", "13006027"])
        self.assertEqual(entity("Zimmah")["bsi"]["review_status"], "source_unreviewed")
        self.assertEqual(entity("Zimmah")["explicit_instances"]["wlc"],
                         [["o130060050061"], ["o130060270041"]])


if __name__ == "__main__":
    unittest.main()
