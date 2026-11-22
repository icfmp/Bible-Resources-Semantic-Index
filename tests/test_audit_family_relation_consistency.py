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

    def test_disallowed_negative_report_limit(self):
        with self.assertRaisesRegex(ValueError, "Negative"):
            family.audit(ROOT / "data", limit=-1)


if __name__ == "__main__":
    unittest.main()
