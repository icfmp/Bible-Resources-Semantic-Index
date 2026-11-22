"""Six verified place source references, without invented lexical tokens."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIED = {
    "Aijalon.2": "07012012",
    "Ain.3": "06021016",
    "Aphik": "07001031",
    "Ashnah.2": "06015043",
    "Ephraim.2": "43011054",
    "Aphek.4": "06013004",
}


class AttestedLocationReferencesTests(unittest.TestCase):
    def test_targeted_location_source_verse_repairs_are_reversible(self):
        for name, verse in VERIFIED.items():
            with self.subTest(name=name):
                p = ROOT / "data" / "entities" / "places" / (name + ".json")
                row = json.loads(p.read_text(encoding="utf-8"))
                self.assertEqual(row["references"], [verse])
                self.assertEqual(row["key_references"], [verse])
                self.assertEqual(row["explicit_instances"], {})
                self.assertEqual(row["bsi"]["review_status"], "source_unreviewed")
                self.assertEqual(len(row["bsi"]["source_sha256"]), 64)
                edits = [x for x in row["bsi"]["editorial_field_changes"]
                         if x["action"] == "add_directly_attested_source_verse"]
                self.assertEqual(len(edits), 1)
                self.assertEqual(edits[0]["added_reference_values"], {
                    "references": [verse]})
                self.assertTrue(edits[0]["evidence"])
                self.assertTrue(edits[0]["reason"])


if __name__ == "__main__":
    unittest.main()
