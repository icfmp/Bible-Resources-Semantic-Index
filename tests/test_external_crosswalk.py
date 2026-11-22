"""External mappings must be source-reviewed, edition-pinned and abstain safely.

All external IDs and evidence in these examples are SYNTHETIC test fixtures;
none is a real approved dictionary/encyclopedia mapping.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_external_crosswalk_validator",
    ROOT / "scripts" / "validate_external_crosswalk.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ExternalCrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / "links" / "schema.v1.json")
                                 .read_text(encoding="utf-8"))
        self.valid_ids = {"person:Mary.2", "place:Gadara"}
        self.doc = {
            "schema_version": 1,
            "resource": {
                "id": "fixture-dictionary",
                "kind": "dictionary",
                "edition": "synthetic-test-edition",
                "revision": "synthetic-snapshot-1",
                "source_url": "https://example.invalid/synthetic-source-edition",
                "license": "Synthetic placeholder, not a real rights clearance",
            },
            "provenance": {
                "bsi_version": "synthetic-test",
                "bsi_source_commit": "a" * 40,
                "review_policy": "manual_source_verified",
            },
            "links": [{
                "entity_id": "person:Mary.2",
                "entry_id": "synthetic-entry-001",
                "relation": "same_subject",
                "review_status": "reviewed",
                "evidence": ["Fixture only; no actual editorial verification"],
            }],
            "abstentions": [{
                "entity_id": "place:Gadara",
                "reason": "ambiguous_entries",
                "candidate_entry_ids": ["synthetic-geo-A", "synthetic-geo-B"],
                "review_status": "withheld",
                "evidence": ["Fixture for ambiguous source headwords, not a real claim"],
            }],
        }

    def check(self, doc=None, identities=None):
        return validator.validate(doc or self.doc,
                                  self.valid_ids if identities is None else identities,
                                  self.schema)

    def test_synthetic_reviewed_link_and_ambiguity_remain_separate(self):
        original = copy.deepcopy(self.doc)
        result = self.check()
        self.assertEqual(result["reviewed_links"], 1)
        self.assertEqual(result["withheld_mappings"], 1)
        self.assertEqual(self.doc, original)

    def test_missing_or_restricted_current_identity_is_never_linkable(self):
        for identity in ("person:Missing", "keyterm:Secret", "person:Quarantined"):
            with self.subTest(identity=identity):
                altered = copy.deepcopy(self.doc)
                altered["links"][0]["entity_id"] = identity
                with self.assertRaisesRegex(ValueError, "absent, quarantined or restricted"):
                    self.check(altered)

    def test_ambiguous_target_must_not_be_auto_selected(self):
        altered = copy.deepcopy(self.doc)
        altered["abstentions"][0]["candidate_entry_ids"] = ["synthetic-geo-A"]
        with self.assertRaisesRegex(ValueError, "at least two candidates"):
            self.check(altered)
        altered["abstentions"][0]["candidate_entry_ids"] = [
            "synthetic-geo-A", "synthetic-geo-A"]
        with self.assertRaisesRegex(ValueError, "Duplicate external candidate"):
            self.check(altered)
        altered["abstentions"][0]["candidate_entry_ids"] = [
            "synthetic-geo-A", "synthetic-geo-B"]
        altered["abstentions"][0]["review_status"] = "reviewed"
        with self.assertRaisesRegex(ValueError, "withheld status"):
            self.check(altered)

    def test_missing_entry_abstention_has_no_fabricated_candidates(self):
        altered = copy.deepcopy(self.doc)
        altered["abstentions"][0]["reason"] = "source_entry_missing"
        with self.assertRaisesRegex(ValueError, "cannot assert existing candidates"):
            self.check(altered)
        altered["abstentions"][0]["candidate_entry_ids"] = []
        self.assertEqual(self.check(altered)["withheld_mappings"], 1)

    def test_source_edition_and_rights_metadata_must_be_present(self):
        for field in ("edition", "revision", "license", "source_url"):
            altered = copy.deepcopy(self.doc)
            del altered["resource"][field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "missing="):
                self.check(altered)
        altered = copy.deepcopy(self.doc)
        altered["resource"]["source_url"] = "file:///unverified-source"
        with self.assertRaisesRegex(ValueError, "HTTP"):
            self.check(altered)
        altered = copy.deepcopy(self.doc)
        altered["provenance"]["bsi_source_commit"] = "short"
        with self.assertRaisesRegex(ValueError, "full BRSI producer commit"):
            self.check(altered)

    def test_unreviewed_auto_guess_is_never_a_published_mapping(self):
        altered = copy.deepcopy(self.doc)
        altered["links"][0]["review_status"] = "candidate"
        with self.assertRaisesRegex(ValueError, "independently reviewed"):
            self.check(altered)
        altered = copy.deepcopy(self.doc)
        altered["links"][0]["relation"] = "same_spelling"
        with self.assertRaisesRegex(ValueError, "independently reviewed"):
            self.check(altered)
        altered = copy.deepcopy(self.doc)
        altered["links"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "source evidence"):
            self.check(altered)
        altered = copy.deepcopy(self.doc)
        altered["links"][0]["article_text"] = "Forbidden copied article prose"
        with self.assertRaisesRegex(ValueError, "unknown="):
            self.check(altered)

    def test_duplicate_mapping_and_duplicate_abstention_are_rejected(self):
        altered = copy.deepcopy(self.doc)
        altered["links"].append(copy.deepcopy(altered["links"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate reviewed external mapping"):
            self.check(altered)
        altered = copy.deepcopy(self.doc)
        altered["abstentions"].append(copy.deepcopy(altered["abstentions"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate withheld external mapping"):
            self.check(altered)

    def test_reviewed_entry_cannot_also_be_withheld_for_same_entity(self):
        altered = copy.deepcopy(self.doc)
        altered["abstentions"][0]["entity_id"] = "person:Mary.2"
        altered["abstentions"][0]["candidate_entry_ids"] = [
            "synthetic-entry-001", "synthetic-geo-B"]
        with self.assertRaisesRegex(ValueError, "conflicts with reviewed external mapping"):
            self.check(altered)

        # A candidate with the same external ID for another biblical identity
        # is not automatically the same subject and remains independently withheld.
        altered["abstentions"][0]["entity_id"] = "place:Gadara"
        self.assertEqual(self.check(altered)["withheld_mappings"], 1)

        # Same identity can still have distinct, independently reviewed and
        # withheld external entries without making a contextual identity claim.
        altered["abstentions"][0]["entity_id"] = "person:Mary.2"
        altered["abstentions"][0]["candidate_entry_ids"] = [
            "synthetic-geo-A", "synthetic-geo-B"]
        self.assertEqual(self.check(altered)["reviewed_links"], 1)

    def test_same_external_entry_cannot_have_two_reviewed_relation_types(self):
        altered = copy.deepcopy(self.doc)
        conflicting = copy.deepcopy(altered["links"][0])
        conflicting["relation"] = "related_subject"
        altered["links"].append(conflicting)
        with self.assertRaisesRegex(ValueError, "Conflicting reviewed relations"):
            self.check(altered)

        # Distinct entries remain independently reviewable for the same entity.
        altered["links"][1]["entry_id"] = "synthetic-entry-002"
        self.assertEqual(self.check(altered)["reviewed_links"], 2)

        # The same source entry may link to a different identity only when
        # reviewed independently; the validator never merges those identities.
        altered["links"][1]["entity_id"] = "place:Gadara"
        self.assertEqual(self.check(altered)["reviewed_links"], 2)

    def test_schema_matches_validator_and_is_backward_compatible_for_links_only(self):
        self.assertFalse(self.schema["additionalProperties"])
        self.assertIn("abstentions", self.schema["properties"])
        self.assertNotIn("abstentions", self.schema["required"])
        self.assertEqual(self.schema["properties"]["resource"]["required"][-1],
                         "revision")
        self.assertEqual(self.schema["properties"]["links"]["items"]
                         ["properties"]["review_status"]["const"], "reviewed")
        self.assertEqual(self.schema["properties"]["abstentions"]["items"]
                         ["properties"]["review_status"]["const"], "withheld")
        altered = copy.deepcopy(self.doc)
        del altered["abstentions"]
        self.assertEqual(self.check(altered)["withheld_mappings"], 0)

    def test_current_repository_has_no_unvalidated_external_crosswalk(self):
        """Read-only discovery also covers future edition files automatically."""
        files = []
        for folder in validator.CROSSWALK_FOLDERS:
            files.extend(sorted((ROOT / "links" / folder).glob("*.json")))
        results = validator.validate_files(files, ROOT / "data")
        self.assertEqual(len(results), len(files))
        for result in results:
            self.assertIn(result["kind"], ("dictionary", "encyclopedia"))


if __name__ == "__main__":
    unittest.main()
