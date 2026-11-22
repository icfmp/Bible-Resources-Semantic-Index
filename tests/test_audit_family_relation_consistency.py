"""BRSI family relation audit is read-only and canonical-identity aware."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_family_audit", ROOT / "scripts" / "audit_family_relation_consistency.py")
family = importlib.util.module_from_spec(spec)
spec.loader.exec_module(family)


def write(folder: Path, name: str, *, canonical=None, gender="male",
          offspring=None, father=None, mother=None) -> None:
    directory = folder / "entities" / "people"
    directory.mkdir(parents=True, exist_ok=True)
    obj = {
        "id": "person:" + name,
        "bsi": {"canonical_id": canonical or "person:" + name},
    }
    if gender is not None:
        obj["gender"] = gender
    if offspring is not None:
        obj["offspring"] = offspring
    if father is not None:
        obj["father"] = father
    if mother is not None:
        obj["mother"] = mother
    (directory / (name + ".json")).write_text(
        json.dumps(obj), encoding="utf-8")


class FamilyInverseTests(unittest.TestCase):
    def test_agreeing_canonical_alias_and_conflicting_claim_are_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write(root, "Dad", offspring=["person:Child"])
            write(root, "DadAlias", canonical="person:Dad",
                  offspring=["person:Child"])
            write(root, "OtherDad", offspring=["person:Child"])
            write(root, "Child", father="person:DadAlias", gender=None)
            write(root, "UnclaimedChild", gender=None)
            write(root, "Unnamed", gender=None,
                  offspring=["person:UnclaimedChild"])
            before = {
                p.name: p.read_bytes()
                for p in (root / "entities" / "people").glob("*.json")
            }
            result = family.audit(root)
            self.assertEqual(result["counts"]["offspring_claims"], 4)
            self.assertEqual(result["counts"]["inverse_claims_agree_canonically"], 2)
            self.assertEqual(result["counts"]["different_named_parent_in_inverse_claim"], 1)
            self.assertEqual(result["counts"]["parent_role_unknown"], 1)
            self.assertEqual(result["conflicting_inverse_claim_examples"][0]["claiming_parent"],
                             "person:OtherDad")
            self.assertEqual(result["conflicting_inverse_claim_examples"][0]["child_named_parent"],
                             "person:DadAlias")
            self.assertEqual(before, {
                p.name: p.read_bytes()
                for p in (root / "entities" / "people").glob("*.json")
            })

    def test_real_mark_case_is_reported_not_mutated(self):
        result = family.audit(ROOT / "data")
        example = next((
            x for x in result["conflicting_inverse_claim_examples"]
            if x["child"] == "person:Mark" and
            x["claiming_parent"] == "person:HusbandOfMary.2"
        ), None)
        # The report may be bounded; use a larger sample for the full corpus
        if example is None:
            result = family.audit(ROOT / "data", limit=100000)
            example = next((
                x for x in result["conflicting_inverse_claim_examples"]
                if x["child"] == "person:Mark" and
                x["claiming_parent"] == "person:HusbandOfMary.2"
            ), None)
        self.assertIsNotNone(example)
        self.assertEqual(example["child_named_parent"], "person:HusbandOfMary")
        self.assertIn("review candidate", result["warning"])

    def test_group_targets_are_not_a_person_genealogy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write(root, "Parent", offspring=["group:Tribe", "group:FormerPerson",
                                             "person:NotLoaded"])
            group = root / "entities" / "groups" / "Tribe.json"
            group.parent.mkdir(parents=True)
            group.write_text(json.dumps({
                "id": "group:Tribe", "type": "group",
                "bsi": {"canonical_id": "group:Tribe"}
            }), encoding="utf-8")
            migrated = root / "entities" / "people" / "FormerPerson.json"
            migrated.write_text(json.dumps({
                "id": "group:FormerPerson", "type": "group",
                "bsi": {"canonical_id": "group:FormerPerson"},
            }), encoding="utf-8")
            result = family.audit(root)
            counts = result["counts"]
            self.assertEqual(result["person_records_scanned"], 1)
            self.assertEqual(counts["offspring_target_nonperson_kind"], 2)
            self.assertEqual(counts["offspring_target_not_found_in_current_entity_data"], 1)
            examples = {
                row["child_target"]: row["target_kind_if_known"]
                for row in result["nonperson_or_unresolved_offspring_examples"]
            }
            self.assertEqual(examples, {
                "group:Tribe": "group",
                "group:FormerPerson": "group",
                "person:NotLoaded": None,
            })

    def test_disallowed_negative_report_limit(self):
        with self.assertRaisesRegex(ValueError, "Negative"):
            family.audit(ROOT / "data", limit=-1)


if __name__ == "__main__":
    unittest.main()
