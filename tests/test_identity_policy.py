"""BRSI identifying hints are short, source-anchored and not biographies."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brsi_identity_policy",
    ROOT / "scripts" / "identity_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

PILOT = (
    "people/Mary.json", "people/Mary.2.json", "people/Mary.3.json",
    "people/Jashar.json", "people/Perez-uzzah.json",
    "people/Johanan.json", "people/Shallum.5.json", "places/Gadara.json",
)


def record(path):
    return json.loads((ROOT / "data" / "entities" / path).read_text(encoding="utf-8"))


class IdentityHintTests(unittest.TestCase):
    def test_pilot_identification_preserves_source_id_and_references(self):
        for path in PILOT:
            with self.subTest(path=path):
                current = record(path)
                policy.validate_identity_hint(current)
                hint = current["bsi"]["identity_hint"]
                self.assertEqual(hint["review_status"], "editorially_reviewed")
                self.assertEqual(hint["language"], "eng")
                self.assertTrue(set(hint["evidence_references"]).issubset(current["references"]))
                self.assertTrue(current["bsi"]["source_id"])
                self.assertEqual(len(current["bsi"]["source_sha256"]), 64)
                for localization in current.get("localizations", {}).values():
                    self.assertNotIn("descriptions", localization)

    def test_three_marys_are_distinct_even_when_names_identical(self):
        trio = [record(p) for p in (
            "people/Mary.json", "people/Mary.2.json", "people/Mary.3.json")]
        self.assertEqual({m["bsi"]["identity_hint"]["name"] for m in trio}, {"Mary"})
        self.assertEqual(len({m["bsi"]["identity_hint"]["qualifier"] for m in trio}), 3)
        self.assertEqual(len({m["id"] for m in trio}), 3)
        self.assertEqual(trio[1]["bsi"]["identity_hint"]["evidence_references"], ["41015040"])
        self.assertIn("Joses", trio[1]["bsi"]["identity_hint"]["qualifier"])

    def test_invalid_evidence_or_unreviewed_hint_is_rejected(self):
        source = record("people/Mary.2.json")
        for change in (
            {"evidence_references": ["41015041"]},
            {"evidence_references": ["41015040", "41015040"]},
            {"evidence_references": ["Mark 15:40"]},
            {"evidence_references": []},
            {"qualifier": "Mary"},
            {"qualifier": "Biography\nLong prose"},
            {"qualifier": "x" * 141},
            {"name": ""},
            {"language": "fra"},
            {"review_status": "source_unreviewed"},
        ):
            with self.subTest(change=change):
                modified = copy.deepcopy(source)
                modified["bsi"]["identity_hint"].update(change)
                with self.assertRaises(ValueError):
                    policy.validate_identity_hint(modified)
        modified = copy.deepcopy(source)
        modified["bsi"]["identity_hint"]["description"] = "Not an index"
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            policy.validate_identity_hint(modified)

    def test_hint_is_optional_and_does_not_promote_entity_review_status(self):
        source = record("people/Mary.2.json")
        self.assertEqual(source["bsi"]["review_status"], "source_unreviewed")
        policy.validate_identity_hint(source)
        source["bsi"].pop("identity_hint")
        policy.validate_identity_hint(source)


if __name__ == "__main__":
    unittest.main()
