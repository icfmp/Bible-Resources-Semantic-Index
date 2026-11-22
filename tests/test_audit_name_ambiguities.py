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
              hint=False, ref="41015040", words=()):
        folder = root / "entities" / ("people" if kind == "person" else "places")
        folder.mkdir(parents=True, exist_ok=True)
        sid = f"{kind}:{stem}"
        record = {
            "id": sid, "type": kind,
            "key_references": [ref],
            "explicit_instances": {"sblgnt": [list(words)]} if words else {},
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

    def test_distinguishing_verse_then_word_without_inventing_prose(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            self.write(data, "Alice", "Alice", ref="41015040")
            self.write(data, "Alice.2", "Alice", ref="41015041")
            self.write(data, "Bob", "Bob", words=["n41015040001"])
            self.write(data, "Bob.2", "Bob", words=["n41015040002"])
            self.write(data, "Carol", "Carol", words=["n41015040003"])
            self.write(data, "Carol.2", "Carol", words=["n41015040003"])
            outcome = audit.audit(data)
            self.assertEqual(outcome["ambiguous_display_name_groups"], 3)
            self.assertEqual(outcome["source_evidence_triage"], {
                "distinct_source_key_verse_for_triage": 2,
                "distinct_original_word_for_triage": 2,
                "not_distinguished_by_key_verses_or_explicit_words": 2,
            })
            self.assertEqual(outcome["unresolved_without_reviewed_hint"], 2)
            self.assertEqual(
                {row["source_id"] for row in outcome["unresolved_source_examples"]},
                {"person:Carol", "person:Carol.2"},
            )
            self.assertTrue(all(
                row["key_references"] == ["41015040"]
                and row["explicit_word_ids"] == ["sblgnt:n41015040003"]
                for row in outcome["unresolved_source_examples"]
            ))

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
