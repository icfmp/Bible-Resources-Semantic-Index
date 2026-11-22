"""V1 canonical identity projection must never publish unreviewed family claims."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_v1_native_identity_projection", ROOT / "scripts" / "build_native_index.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

WITHHELD_FAMILY = frozenset({
    "father", "mother", "offspring", "partners", "spouse",
    "wives", "husbands", "sons", "daughters", "children",
    "group_origin", "referred_to_as",
})
WITHHELD_LOCALIZATIONS = frozenset({"localizations", "alternate_labels"})


class V1AbstentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = native.build(ROOT / "data")

    def test_public_identity_projection_does_not_copy_source_family_or_aliases(self):
        for row in self.index["entities"]:
            self.assertFalse(set(row) & WITHHELD_FAMILY, row["id"])
            self.assertFalse(set(row) & WITHHELD_LOCALIZATIONS, row["id"])
        self.assertEqual(self.index["distribution_profile"]["excluded_kinds"],
                         ["keyterm"])

    def test_real_source_conflicts_preserve_original_word_witnesses(self):
        by_id = {row["id"]: row for row in self.index["entities"]}
        for name in ("Jesher", "Shobab.2", "Ardon"):
            self.assertEqual(by_id["person:" + name]["references"], ["13002018"])
        self.assertEqual(by_id["person:Zimmah"]["references"],
                         ["13006005", "13006027"])
        self.assertEqual(by_id["person:Zimmah"]["occurrences"]
                         ["explicit_instances"]["wlc"],
                         [["o130060050061"], ["o130060270041"]])
        self.assertEqual(by_id["place:Gerasa"]["occurrences"]
                         ["explicit_instances"]["SBLGNT"],
                         [["n40008028011"], ["n41005001012"],
                          ["n42008026007"], ["n42008037010"]])
        self.assertIn("person:Mark", by_id)
        self.assertIn("person:Mary.5", by_id)
        self.assertIn("person:HusbandOfMary", by_id)
        self.assertEqual(by_id["person:HusbandOfMary"]["review_status"],
                         "source_unreviewed")

    def test_disputed_genealogy_source_records_have_a_reversible_withhold_receipt(self):
        affected = (
            "Mark", "Mary.5", "Mary.2", "HusbandOfMary", "HusbandOfMary.2",
            "Ardon", "Jesher", "Shobab.2", "Azubah.2",
            "Zimmah", "Jahath.2", "Shimei.2",
        )
        for name in affected:
            record = json.loads(
                (ROOT / "data" / "entities" / "people" /
                 (name + ".json")).read_text(encoding="utf-8"))
            receipts = [x for x in record["bsi"]["editorial_field_changes"]
                        if x["action"] == "withhold_inferred_genealogical_identity"]
            self.assertTrue(receipts, name)
            self.assertEqual(record["bsi"]["review_status"], "source_unreviewed")
            for receipt in receipts:
                self.assertTrue(receipt["removed_fields"], name)
                self.assertTrue(receipt["evidence"], name)
                self.assertTrue(receipt["reason"].strip(), name)
                for field in receipt["removed_fields"]:
                    self.assertNotIn(field, record, (name, field))
                    self.assertEqual(set(receipt["removed_relation_values"]), {field})
                    self.assertTrue(receipt["removed_relation_values"][field])
                    self.assertTrue(all(
                        isinstance(x, str) and x for x in
                        receipt["removed_relation_values"][field]))


if __name__ == "__main__":
    unittest.main()
