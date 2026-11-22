"""Permanent guard: BRSI native entities must never carry encyclopedia prose."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "entities"


class IndexOnlyEntityTests(unittest.TestCase):
    def test_all_native_entities_exclude_multilingual_descriptions(self):
        scanned = 0
        for path in sorted(DATA.glob("*/*.json")):
            with self.subTest(path=path.relative_to(DATA).as_posix()):
                obj = json.loads(path.read_text(encoding="utf-8"))
                scanned += 1
                self.assertIn("bsi", obj, path)
                self.assertIn("source_id", obj["bsi"], path)
                self.assertIn("canonical_id", obj["bsi"], path)
                self.assertIn("references", obj, path)
                self.assertIn("key_references", obj, path)
                self.assertNotIn("descriptions", obj, path)
                localization = obj.get("localizations", {})
                self.assertIsInstance(localization, dict, path)
                for language, fields in localization.items():
                    self.assertIsInstance(fields, dict, (path, language))
                    self.assertNotIn("descriptions", fields, (path, language))
                meta = obj["bsi"].get("inherited_localizations", {})
                self.assertNotIn("descriptions", meta.get("fields", []), path)
        self.assertGreater(scanned, 0)

    def test_original_keyterm_category_not_materialized(self):
        self.assertFalse((DATA / "keyterms").exists())


if __name__ == "__main__":
    unittest.main()
