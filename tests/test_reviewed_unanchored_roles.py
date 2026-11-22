"""Source witnesses distinguish unanchored background geography from biblical roles."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def record(path):
    return json.loads((ROOT / "data" / "entities" / path).read_text(encoding="utf-8"))


class UnanchoredRoleReviewTests(unittest.TestCase):
    def test_solo_narrative_role_has_specific_evidence_not_fabricated_name_word(self):
        second = record("people/SecondProstitute.json")
        hint = second["bsi"]["identity_hint"]
        self.assertEqual(hint["review_status"], "editorially_reviewed")
        self.assertEqual(hint["evidence_references"], ["11003022"])
        self.assertEqual(second["bsi"]["review_status"], "source_unreviewed")
        self.assertEqual(second["explicit_instances"], {})
        self.assertIn("wlc", second["pronominal_referents"])
        self.assertTrue(any(
            edit["action"] == "add_source_anchored_role_identity_hint"
            for edit in second["bsi"]["editorial_field_changes"]))

    def test_assyrian_background_place_is_not_falsely_marked_biblical(self):
        uqnu = record("places/Uqnu.json")
        self.assertFalse(uqnu["mentioned_in_bible"])
        self.assertTrue(uqnu["non_biblical"])
        self.assertEqual(uqnu["references"], [])
        self.assertEqual(uqnu["key_references"], [])
        self.assertEqual(uqnu["explicit_instances"], {})
        edit = uqnu["bsi"]["editorial_field_changes"][-1]
        self.assertEqual(edit["replaced_field_values"], {
            "mentioned_in_bible": {"from": True, "to": False},
            "non_biblical": {"from": False, "to": True},
        })
        self.assertEqual(uqnu["bsi"]["review_status"], "source_unreviewed")


if __name__ == "__main__":
    unittest.main()
