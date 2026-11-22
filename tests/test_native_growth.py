"""Native BSI editing must permit new evidenced records and protect all imported IDs."""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_bsi_builder", ROOT / "scripts" / "build_native_index.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class NativeGrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"
        shutil.copytree(ROOT / "data", self.data)

    def add_native_work(self):
        work = self.data / "entities" / "works"
        work.mkdir(exist_ok=True)
        path = work / "Fixture.json"
        path.write_text(json.dumps({
            "id": "work:Fixture", "primary_id": "work:Fixture",
            "type": "literary_work", "references": ["01001001"],
            "key_references": ["01001001"],
            "bsi": {
                "origin": "bsi", "source_id": "bsi:work:Fixture",
                "source_primary_id": "bsi:work:Fixture",
                "canonical_id": "work:Fixture",
                "review_status": "editorially_reviewed",
                "editorial_reason": "Synthetic test case, not a real biblical entity",
                "editorial_evidence": ["Test fixture only: Genesis 1:1"],
            },
        }, ensure_ascii=False), encoding="utf-8")
        return path

    def test_current_builder_does_not_import_historical_compiler(self):
        self.assertEqual(Path(builder.core.__file__).name, "entity_index_core.py")
        self.assertNotIn("compile_index.py",
                         (ROOT / "scripts" / "build_native_index.py").read_text())

    def test_new_reviewed_entity_does_not_rewrite_historical_baseline(self):
        baseline = builder.build(self.data)
        path = self.add_native_work()
        current = builder.build(self.data)
        self.assertEqual(len(current["entities"]), len(baseline["entities"]) + 1)
        self.assertEqual(len(current["quarantined"]), len(baseline["quarantined"]))
        self.assertEqual(current["statistics"]["source_records"], baseline["statistics"]["source_records"])
        self.assertEqual(current["by_word"], baseline["by_word"])
        self.assertEqual(current["unattested_source_words"], baseline["unattested_source_words"])
        self.assertEqual(current["unattested_source_verses"], baseline["unattested_source_verses"])
        self.assertEqual(current["qualified_source_references"], baseline["qualified_source_references"])
        old = {e["source_id"]: e for e in baseline["entities"]}
        new = {e["source_id"]: e for e in current["entities"]}
        self.assertEqual({sid: new[sid] for sid in old}, old)
        self.assertEqual(new["bsi:work:Fixture"]["id"], "work:Fixture")
        self.assertIsNone(new["bsi:work:Fixture"]["source_sha256"])
        self.assertTrue(path.exists())

    def test_nonworking_translated_names_are_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["localizations"]["fra"] = {"preferred_label": "Marie"}
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Redundant translated label"):
            builder.build(self.data)

    def test_source_biographies_are_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["localizations"]["eng"]["descriptions"] = [
            {"description": "Old inherited paragraph"}
        ]
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Encyclopedia descriptions forbidden"):
            builder.build(self.data)

    def test_historical_source_cannot_disappear(self):
        (self.data / "entities" / "people" / "Jashar.json").unlink()
        with self.assertRaisesRegex(ValueError, "Imported ACAI entity identities changed"):
            builder.build(self.data)

    def test_unreviewed_new_native_entry_is_rejected(self):
        path = self.add_native_work()
        payload = json.loads(path.read_text())
        del payload["bsi"]["editorial_evidence"]
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lacks source evidence"):
            builder.build(self.data)

    def test_source_id_mismatch_is_rejected(self):
        path = self.add_native_work()
        payload = json.loads(path.read_text())
        payload["bsi"]["source_id"] = "bsi:person:WrongCategory"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Incorrect BSI-native identity"):
            builder.build(self.data)


if __name__ == "__main__":
    unittest.main()
