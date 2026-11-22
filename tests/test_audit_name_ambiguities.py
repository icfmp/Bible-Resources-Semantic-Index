"""Name-collision auditing never treats names or source aliases as identity proof."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_name_audit", ROOT / "scripts" / "audit_name_ambiguities.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class NameCandidateAuditTests(unittest.TestCase):
    def write(self, root, stem, label, canonical=None, kind="person",
              hint=False):
        folder = root / "entities" / ("people" if kind == "person" else "places")
        folder.mkdir(parents=True, exist_ok=True)
        sid = f"{kind}:{stem}"
        record = {
            "id": sid, "type": kind,
            "key_references": ["41015040"],
            "bsi": {"canonical_id": canonical or sid, "source_id": sid},
            "localizations": {"eng": {"preferred_label": label}},
        }
        if hint:
            record["bsi"]["identity_hint"] = {"review_status": "editorially_reviewed"}
        (folder / (stem + ".json")).write_text(json.dumps(record), encoding="utf-8")

    def test_collisions_require_distinct_canonical_entities(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            self.write(data, "Mary", "Mary (Mother of Jesus)", hint=True)
            self.write(data, "Mary.2", "Mary", hint=True)
            self.write(data, "Mary.3", "Mary (of Bethany)")
            self.write(data, "AliasMary", "Mary", canonical="person:Mary")
            self.write(data, "CityMary", "Mary", kind="place")
            result = audit.audit(data)
            self.assertEqual(result["source_records_scanned"], 5)
            self.assertEqual(result["ambiguous_display_name_groups"], 1)
            self.assertEqual(result["records_in_groups"], 4)
            self.assertEqual(result["records_without_reviewed_hint"], 2)
            group = result["sample_groups"][0]
            self.assertEqual(group["normalized_source_name"], "mary")
            self.assertEqual(group["distinct_canonical_id_count"], 3)
            self.assertEqual(group["kind"], "person")
            self.assertEqual(group["candidate_record_count"], 4)
            self.assertEqual(audit.audit(data, sample_limit=0)["sample_groups"], [])

    def test_same_source_identity_alias_is_not_a_homonym(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            self.write(data, "James", "James")
            self.write(data, "JamesAlias", "James (alternate)", canonical="person:James")
            self.assertEqual(audit.audit(data)["ambiguous_display_name_groups"], 0)

    def test_only_final_parenthetical_qualifier_is_removed(self):
        self.assertEqual(audit.base_name("Mary (of Bethany)"), "mary")
        self.assertEqual(audit.base_name(" Mary  "), "mary")
        self.assertEqual(audit.base_name("Mary (one) (two)"), "mary (one)")
        with self.assertRaisesRegex(ValueError, "Empty"):
            audit.base_name("  ")


if __name__ == "__main__":
    unittest.main()
