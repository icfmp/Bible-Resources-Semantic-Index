"""Check editorial field edits are documented and do not leave contradictions."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HUMAN_FIELDS = {"father", "mother", "siblings", "spouse", "wives", "husbands",
                "children", "sons", "daughters", "parents", "gender"}
CATEGORIES = {"people": "person", "places": "place", "groups": "group",
              "deities": "deity", "fauna": "fauna", "flora": "flora",
              "realia": "realia"}


class EditorialFieldProvenance(unittest.TestCase):
    def test_all_documented_removals_are_absent_with_evidence(self):
        count = 0
        for path in sorted((DATA / "entities").rglob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            meta = record["bsi"]
            for edit in meta.get("editorial_field_changes", []):
                count += 1
                self.assertTrue(edit["reason"].strip(), path)
                self.assertTrue(edit["evidence"], path)
                self.assertTrue(all(isinstance(x, str) and x.strip()
                                    for x in edit["evidence"]), path)
                for field in edit.get("removed_fields", []):
                    self.assertNotIn(field, record, (path, field))
                for field, values in edit.get("removed_relation_values", {}).items():
                    self.assertTrue(all(value not in record.get(field, [])
                                        for value in values), (path, field))
        self.assertGreater(count, 0)

    def test_approved_reclassification_does_not_retain_human_attributes(self):
        decisions = json.loads((DATA / "editorial-decisions.json").read_text())["decisions"]
        changed = {row["source_id"] for row in decisions
                   if row["action"] == "replace_identity" and row["source_id"].startswith("person:")}
        for path in sorted((DATA / "entities").rglob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            source_id = record["bsi"]["source_id"]
            if source_id in changed and record["type"] != "person":
                self.assertFalse(HUMAN_FIELDS.intersection(record),
                                 (path, HUMAN_FIELDS.intersection(record)))


if __name__ == "__main__":
    unittest.main()
