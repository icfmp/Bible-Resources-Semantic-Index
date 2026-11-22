"""Unqualified inherited offspring labels cannot enter typed BRSI relations."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_offspring_target_policy", ROOT / "scripts" / "offspring_target_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class TypedOffspringTests(unittest.TestCase):
    def test_mizraim_links_to_existing_ludim_group_without_source_edits(self):
        egypt = json.loads((ROOT / "data/entities/people/Egypt.json").read_text())
        ludim = json.loads((ROOT / "data/entities/groups/Ludim.json").read_text())
        original = copy.deepcopy(egypt)
        policy.validate_offspring_targets(egypt)
        self.assertEqual(egypt, original)
        self.assertIn("group:Ludim", egypt["offspring"])
        self.assertNotIn("Ludim@Gen.10.13-1Ch", egypt["offspring"])
        self.assertEqual(ludim["id"], "group:Ludim")
        self.assertEqual(ludim["bsi"]["source_id"], "group:Ludim")
        self.assertEqual(ludim["key_references"], ["01010013", "13001011"])
        self.assertEqual(egypt["bsi"]["review_status"], "source_unreviewed")
        old_new = egypt["bsi"]["editorial_field_changes"][0]["replaced_relation_values"]["offspring"]
        self.assertIn("Ludim@Gen.10.13-1Ch", old_new["from"])
        self.assertIn("group:Ludim", old_new["to"])
        self.assertEqual(egypt["offspring"], old_new["to"])

    def test_accepts_collective_descendants_and_preserves_order(self):
        source = {"offspring": ["person:Child", "group:Tribe",
                                "group:Tribe", "work:SomeText"]}
        original = copy.deepcopy(source)
        policy.validate_offspring_targets(source)
        self.assertEqual(source, original)
        policy.validate_offspring_targets({})

    def test_rejects_legacy_tipnr_and_untyped_or_malformed_values(self):
        for value in ("Ludim@Gen.10.13-1Ch", "", None, 123,
                      "person", "person:", " group:Ludim",
                      "group:Ludim name", "group::Ludim"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "typed entity ID"):
                policy.validate_offspring_targets({"offspring": [value]})
        for payload in (None, "group:Ludim", {}):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "list"):
                policy.validate_offspring_targets({"offspring": payload})


if __name__ == "__main__":
    unittest.main()
