"""Synthetic non-mutating BSI entity relation audit regression tests."""
from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_entity_relationships.py"
spec = importlib.util.spec_from_file_location("relation_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class RelationshipAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        (self.data / "entities" / "people").mkdir(parents=True)
        (self.data / "entities" / "places").mkdir(parents=True)
        (self.data / "quarantined" / "people").mkdir(parents=True)

    def record(self, folder, name, new_id, source_id, **extra):
        doc = {"id": new_id, "bsi": {"source_id": source_id}, **extra}
        path = self.data / folder / (name + ".json")
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_old_and_missing_structured_links_are_reported_without_mutation(self):
        one = self.record("entities/people", "A", "person:A", "person:A",
                          partner="place:Old", offspring=["person:Absent", "keyterm:Grace"],
                          localizations={"eng": {"description": "person:Old"}},
                          alternate_sources={"source": "person:Missing"})
        self.record("entities/places", "Old", "place:New", "place:Old")
        before = one.read_bytes()
        result = audit.audit(self.data)
        self.assertEqual(result["classifications"]["old_identity"], 1)
        self.assertEqual(result["classifications"]["unresolved_identity"], 1)
        self.assertEqual(result["classifications"]["restricted_keyterm_unavailable"], 1)
        self.assertEqual(len(result["review_candidates"]), 2)
        self.assertEqual(result["review_candidates"][1]["target"], "place:Old")
        self.assertEqual(one.read_bytes(), before)

    def test_quarantined_links_and_duplicate_source_ids(self):
        self.record("entities/people", "A", "person:A", "person:A",
                    partner="person:Quarantined")
        self.record("quarantined/people", "Q", "person:Quarantined", "person:Quarantined")
        report = audit.audit(self.data)
        self.assertEqual(report["classifications"]["current_to_quarantined"], 1)
        self.record("entities/places", "B", "place:B", "person:A")
        with self.assertRaisesRegex(ValueError, "Duplicate original ID"):
            audit.audit(self.data)


if __name__ == "__main__":
    unittest.main()
