"""The BRSI native source tree stores only one working-language name."""
from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "entities"


class OneLanguageIdentityTests(unittest.TestCase):
    def test_all_current_entities_use_only_english_working_labels(self):
        seen = Counter()
        for path in sorted(DATA.glob("*/*.json")):
            with self.subTest(path=path.relative_to(DATA).as_posix()):
                record = json.loads(path.read_text(encoding="utf-8"))
                labels = record.get("localizations", {})
                self.assertIsInstance(labels, dict)
                self.assertEqual(set(labels), {"eng"})
                self.assertIsInstance(labels["eng"].get("preferred_label"), str)
                self.assertTrue(labels["eng"]["preferred_label"].strip())
                self.assertNotIn("descriptions", labels["eng"])
                hold = record["bsi"].get("inherited_localizations", {})
                self.assertTrue(all(
                    "." not in s or s.startswith("eng.")
                    for s in hold.get("fields", [])
                ))
                seen[record["type"]] += 1
        self.assertGreater(sum(seen.values()), 0)
        self.assertIn("person", seen)
        self.assertIn("place", seen)

    def test_reviewed_hints_do_not_require_translations(self):
        for basename in ("Mary.json", "Mary.2.json", "Mary.3.json"):
            record = json.loads((DATA / "people" / basename).read_text(encoding="utf-8"))
            hint = record["bsi"]["identity_hint"]
            self.assertEqual(hint["language"], "eng")
            self.assertTrue(set(hint["evidence_references"]).issubset(record["references"]))
            self.assertEqual(set(record["localizations"]), {"eng"})


if __name__ == "__main__":
    unittest.main()
