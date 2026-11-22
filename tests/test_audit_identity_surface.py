"""The identity inventory is read-only and never copies actual descriptions."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_identity_audit", ROOT / "scripts" / "audit_identity_surface.py")
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class IdentityInventoryTests(unittest.TestCase):
    def test_aggregated_counts_and_no_source_prose_in_report(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            path = base / "entities" / "people" / "sample.json"
            path.parent.mkdir(parents=True)
            data = {
                "id": "person:A", "type": "person",
                "bsi": {"review_status": "source_unreviewed"},
                "localizations": {
                    "eng": {
                        "preferred_label": "A",
                        "alternate_labels": ["Sensitive alias"],
                        "descriptions": [{"description": "Sensitive biography"}],
                    },
                    "fra": {"preferred_label": "B"},
                },
                "roles": ["Not a biography field"],
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            result = audit_module.audit(base)
            self.assertEqual(result["records"], 1)
            self.assertEqual(result["description_fields_remaining"], 1)
            self.assertEqual(result["source_labels_by_language"], {"eng": 1, "fra": 1})
            self.assertEqual(result["source_alias_sets_by_language"], {"eng": 1})
            self.assertEqual(result["non_label_source_field_presence"]["roles"], 1)
            self.assertNotIn("Sensitive", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
