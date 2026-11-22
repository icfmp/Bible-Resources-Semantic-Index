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
                "references": [], "key_references": ["06011008"],
                "mentioned_in_bible": True, "explicit_instances": {},
                "bsi": {"source_id": "person:A", "review_status": "source_unreviewed"},
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
            review = result["reference_shape_triage"]
            self.assertEqual(review["key_refs_not_in_references_count"], 1)
            self.assertEqual(review["biblical_flag_without_reference_or_word_count"], 1)
            self.assertEqual(review["key_ref_examples"][0]["source_id"], "person:A")
            self.assertEqual(review["unanchored_biblical_entity_examples"][0]["key_references"], ["06011008"])
            self.assertEqual(json.loads(path.read_text()), data)


if __name__ == "__main__":
    unittest.main()
