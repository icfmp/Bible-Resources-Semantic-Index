"""Auditor must report inherited source contradictions without editing them."""
from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bsi_reclassified_audit", ROOT / "scripts" / "audit_reclassified_entity_fields.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class ReclassifiedEntityTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.data = Path(t.name)
        (self.data / "entities" / "people").mkdir(parents=True)
        (self.data / "entities" / "places").mkdir(parents=True)
        (self.data / "editorial-decisions.json").write_text(json.dumps({"decisions": [
            {"source_id": "person:Perez-uzzah", "action": "replace_identity"},
        ]}), encoding="utf-8")

    def make(self, folder, name, doc):
        path = self.data / "entities" / folder / (name + ".json")
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_changed_kind_flags_inherited_fields_without_mutation(self):
        a = {"id": "place:PerezUzzah", "type": "place",
             "bsi": {"source_id": "person:Perez-uzzah", "canonical_id": "place:PerezUzzah",
                     "editorial_reason": "A place rather than a human"},
             "father": "person:Abinadab",
             "referred_to_as": ["person:Uzzah"],
             "localizations": {"eng": {"descriptions": [{
                 "source": "acai", "article": "person:Perez-uzzah",
                 "description": "An inherited unreviewed description"}]}}}
        path = self.make("people", "Perez-uzzah", a)
        self.make("places", "Jordan", {"id": "place:Jordan", "type": "place",
                  "bsi": {"source_id": "place:Jordan", "canonical_id": "place:Jordan"}})
        before = path.read_bytes()
        d = tool.audit(self.data)
        self.assertEqual(d["reviewed_changed_identity_records"], 1)
        row = d["items"][0]
        self.assertEqual(row["person_specific_fields"], ["father"])
        self.assertIn("inherited_unreviewed_descriptions", row["issue_codes"])
        self.assertIn("inherited_person_specific_fields", row["issue_codes"])
        self.assertEqual(row["source_descriptions"][0]["article"], "person:Perez-uzzah")
        self.assertEqual(path.read_bytes(), before)

    def test_same_kind_canonical_identity_change_still_reviewed(self):
        (self.data / "editorial-decisions.json").write_text(json.dumps({"decisions": [
            {"source_id": "person:A", "action": "replace_identity"},
        ]}), encoding="utf-8")
        self.make("people", "A", {"id": "person:A", "type": "person",
                  "bsi": {"source_id": "person:A", "canonical_id": "person:B"},
                  "localizations": {"fra": {"preferred_label": "A"}}})
        result = tool.audit(self.data)
        self.assertEqual(result["reviewed_changed_identity_records"], 1)
        self.assertIn("canonical_identity_changed", result["items"][0]["issue_codes"])


if __name__ == "__main__":
    unittest.main()
