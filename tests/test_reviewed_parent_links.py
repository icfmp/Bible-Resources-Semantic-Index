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
        self.assertIn("Genesis 19:36-38", " ".join(change["evidence"]))

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

    def test_new_evidence_does_not_assert_other_unverified_fathers(self):
        # The unrelated source-only unnamed-husband claim remains for
        # manual biblical source review, not silently merged or fixed.
        self.assertIn("person:Mark", entity("HusbandOfMary.2")["offspring"])
        self.assertEqual(entity("Mark")["father"], "person:HusbandOfMary")


if __name__ == "__main__":
    unittest.main()
