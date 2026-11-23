"""Pinned WLC identifications: two unrelated returnee names and uncertain mountains."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def entity(category, name):
    return json.loads((ROOT / "data" / "entities" / category / (name + ".json")).read_text(encoding="utf-8"))


class DistinctZaccaiAndZalmonTests(unittest.TestCase):
    def test_zaccai_is_not_zabbai_the_father_of_baruch(self):
        zaccai = entity("people", "Zaccai")
        zabbai = entity("people", "Zabbai.2")
        self.assertEqual(zaccai["bsi"]["canonical_id"], "person:Zaccai")
        self.assertEqual(zaccai["primary_id"], "person:Zaccai")
        self.assertEqual(zaccai["bsi"]["source_primary_id"], "person:Zabbai.2")
        self.assertEqual(zaccai["references"], ["15002009", "16007014"])
        self.assertEqual(zaccai["explicit_instances"]["wlc"],
                         [["o150020090021"], ["o160070140021"]])
        self.assertNotIn("16003020", zaccai["references"])
        self.assertNotIn("o160030200071", sum(zaccai["explicit_instances"]["wlc"], []))
        self.assertEqual(zabbai["references"], ["16003020"])
        self.assertEqual(zabbai["explicit_instances"]["wlc"], [["o160030200071"]])
        self.assertNotIn("Zaccai", zabbai["localizations"]["eng"].get("alternate_labels", []))
        self.assertNotIn("referred_to_as", zabbai)
        self.assertNotIn("referred_to_as", zaccai)

    def test_ebal_exact_words_are_not_zalmon_exact_words(self):
        ebal = entity("places", "EbalMount")
        psalm = entity("places", "Zalmon")
        judges = entity("places", "ZalmonMount")
        ebal_words = [w for group in ebal["explicit_instances"]["wlc"] for w in group]
        self.assertNotIn("o070090480041", ebal_words)
        self.assertNotIn("o190680150062", ebal_words)
        self.assertNotIn("07009048", ebal["references"])
        self.assertNotIn("19068015", ebal["references"])
        self.assertNotIn("referred_to_as", ebal)
        self.assertFalse({"Zalmon", "Mount Zalmon"} &
                         set(ebal["localizations"]["eng"].get("alternate_labels", [])))
        self.assertEqual(psalm["explicit_instances"]["wlc"], [["o190680150062"]])
        self.assertEqual(judges["explicit_instances"]["wlc"], [["o070090480041"]])
        for row, ident in [(psalm, "place:Zalmon"), (judges, "place:ZalmonMount")]:
            self.assertEqual(row["primary_id"], ident)
            self.assertEqual(row["bsi"]["canonical_id"], ident)
            self.assertEqual(row["bsi"]["source_primary_id"], "place:EbalMount")
            self.assertNotIn("geocoordinates", row)
            self.assertNotIn("Mount Ebal", row["localizations"]["eng"].get("alternate_labels", []))
            self.assertNotIn("referred_to_as", row)
        self.assertIn("place:Zalmon", judges["possibly_same_as"])
        self.assertIn("place:ZalmonMount", psalm["possibly_same_as"])
        self.assertIn("19068015", judges["key_references"])

    def test_all_five_source_changes_have_reversible_evidence(self):
        for kind, name in [("people", "Zaccai"), ("people", "Zabbai.2"),
                           ("places", "EbalMount"), ("places", "Zalmon"),
                           ("places", "ZalmonMount")]:
            record = entity(kind, name)
            bsi = record["bsi"]
            self.assertEqual(bsi["review_status"], "editorially_reviewed")
            self.assertEqual(len(bsi["source_sha256"]), 64)
            self.assertTrue(bsi["editorial_reason"])
            self.assertTrue(bsi["editorial_evidence"])
            receipt = bsi["editorial_field_changes"][-1]
            self.assertTrue(receipt["action"])
            self.assertIn("before", receipt["replaced_field_values"])
            self.assertIn("after", receipt["replaced_field_values"])
            self.assertTrue(receipt["evidence"])

if __name__ == "__main__":
    unittest.main()
