"""Biblical name attestation is not later-place nomenclature or an unpinned reading."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def place(name):
    return json.loads((ROOT/"data"/"entities"/"places"/(name+".json")).read_text(encoding="utf-8"))

class SourceScopeDistinctionTests(unittest.TestCase):
    def test_four_later_or_variant_names_cannot_claim_direct_biblical_mention(self):
        expected={
            "Batanea":(["05032014"],["Bashan"]),
            "Magdala":(["40015039"],[]),
            "RedSea.2":(["11009026"],["Red Sea"]),
            "RedSea.3":(["02010019","04033010","04033011"],["Red Sea"]),
        }
        for name,(keys,invalid_aliases) in expected.items():
            with self.subTest(name=name):
                r=place(name)
                self.assertFalse(r["mentioned_in_bible"])
                self.assertTrue(r["non_biblical"])
                self.assertEqual(r["key_references"],keys)
                self.assertEqual(r["references"],[])
                self.assertEqual(r["explicit_instances"],{})
                self.assertTrue(all(a not in r["localizations"]["eng"].get("alternate_labels", [])
                                    for a in invalid_aliases))
                receipt=r["bsi"]["editorial_field_changes"][-1]
                self.assertEqual(receipt["action"],
                    "remove_unattested_modern_or_variant_place_name_scope")
                self.assertEqual(receipt["replaced_field_values"]["before"]["mentioned_in_bible"],True)
                self.assertEqual(receipt["replaced_field_values"]["after"]["mentioned_in_bible"],False)
                self.assertTrue(receipt["evidence"])
                self.assertTrue(receipt["reason"])

    def test_bashan_original_is_not_later_batanea_synonym(self):
        modern=place("Batanea")
        ancient=place("Bashan")
        self.assertNotIn("referred_to_as",modern)
        self.assertIn("05032014",ancient["references"])
        self.assertIn("Batanaea",modern["localizations"]["eng"]["alternate_labels"])

    def test_red_sea_original_entity_preserved(self):
        original=place("RedSea")
        self.assertTrue(original["mentioned_in_bible"])
        self.assertTrue(original["explicit_instances"])
        self.assertIn("11009026",original["references"])

    def test_magadan_vs_magdala_edition_limit(self):
        modern=place("Magdala")
        self.assertEqual(modern["key_references"],["40015039"])
        self.assertNotIn("40015039",modern["references"])
        self.assertTrue(any("Μαγαδάν" in claim or "Magadan" in claim
                            for claim in modern["bsi"]["editorial_evidence"]))

if __name__ == "__main__":
    unittest.main()
