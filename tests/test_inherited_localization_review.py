"""Review status of inherited ACAI localizations must remain explicit and reversible."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "people/Jashar.json": ("work:BookOfJashar", set()),
    "people/Perez-uzzah.json": ("place:PerezUzzah", {"preferred_label", "alternate_labels"}),
    "people/Johanan.json": ("person:Johanan", {"preferred_label", "alternate_labels"}),
    "people/Shallum.5.json": ("person:Shallum.5", set()),
    "places/Gadara.json": ("place:Gadara", {"eng.alternate_labels"}),
}


class InheritedLocalizationReviewTests(unittest.TestCase):
    def test_affected_localizations_are_explicitly_withheld(self):
        for path, (expected_id, fields) in CASES.items():
            with self.subTest(path=path):
                record = json.loads((ROOT / "data/entities" / path).read_text(encoding="utf-8"))
                self.assertEqual(record["id"], expected_id)
                metadata = record["bsi"].get("inherited_localizations")
                self.assertEqual(set(metadata["fields"]) if metadata else set(), fields)
                if metadata:
                    self.assertEqual(metadata["status"], "withheld_pending_review")
                    self.assertEqual(metadata["source"], "acai")
                    self.assertTrue(metadata["reason"].strip())
                for localized in record.get("localizations", {}).values():
                    self.assertNotIn("descriptions", localized)

    def test_two_false_person_aliases_are_removed_with_receipts(self):
        for path, alias in (("people/Johanan.json", "Jehoahaz"),
                            ("people/Perez-uzzah.json", "Uzzah")):
            with self.subTest(path=path):
                record = json.loads((ROOT / "data/entities" / path).read_text(encoding="utf-8"))
                self.assertNotIn(alias, record["localizations"]["eng"].get("alternate_labels", []))
                decisions = [x for x in record["bsi"].get("editorial_field_changes", [])
                             if x["action"] == "remove_conflicting_inherited_english_alias"]
                self.assertEqual(len(decisions), 1)
                self.assertEqual(decisions[0]["removed_localization_values"]["eng"]["alternate_labels"], [alias])


if __name__ == "__main__":
    unittest.main()
