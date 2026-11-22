"""Prose pruning is reversible via pinned source, idempotent, and field-scoped."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_prune_descriptions", ROOT / "scripts" / "prune_inherited_descriptions.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def fixture(*, held=True):
    out = {
        "id": "person:Fixture", "type": "person",
        "references": ["41015040"], "key_references": ["41015040"],
        "explicit_instances": {"sblgnt": [["n41015040004"]]},
        "father": "person:Parent",
        "bsi": {
            "source_id": "person:Fixture",
            "source_sha256": "0" * 64,
            "canonical_id": "person:Fixture",
            "review_status": "source_unreviewed",
            "editorial_field_changes": [{"action": "reviewed", "reason": "Keep"}],
        },
        "localizations": {
            "eng": {
                "preferred_label": "Fixture",
                "alternate_labels": ["Other Fixture"],
                "descriptions": [{"description": "Unneeded biography"}],
            },
            "fra": {
                "preferred_label": "Personne",
                "descriptions": [{"description": "Texte source"}],
            },
        },
    }
    if held:
        out["bsi"]["inherited_localizations"] = {
            "status": "withheld_pending_review",
            "fields": ["descriptions", "eng.alternate_labels"],
            "source": "acai", "reason": "Inherited source uncertainty",
        }
    return out


class PruneDescriptionsTests(unittest.TestCase):
    def test_removes_prose_only_and_retains_every_other_value(self):
        original = fixture()
        before = copy.deepcopy(original)
        cleaned, rows, fields, holds = tool.prune_record(original)
        self.assertEqual(original, before)
        self.assertEqual((rows, fields, holds), (2, 2, True))
        for lang in ("eng", "fra"):
            self.assertNotIn("descriptions", cleaned["localizations"][lang])
        self.assertEqual(cleaned["localizations"]["eng"]["alternate_labels"],
                         ["Other Fixture"])
        self.assertEqual(cleaned["bsi"]["inherited_localizations"]["fields"],
                         ["eng.alternate_labels"])
        expected = copy.deepcopy(original)
        for lang in ("eng", "fra"):
            del expected["localizations"][lang]["descriptions"]
        expected["bsi"]["inherited_localizations"]["fields"] = ["eng.alternate_labels"]
        self.assertEqual(cleaned, expected)

    def test_only_descriptions_hold_is_cleared(self):
        record = fixture()
        record["bsi"]["inherited_localizations"]["fields"] = ["descriptions"]
        cleaned, _, _, removed = tool.prune_record(record)
        self.assertTrue(removed)
        self.assertNotIn("inherited_localizations", cleaned["bsi"])
        self.assertEqual(tool.prune_record(cleaned), (cleaned, 0, 0, False))

    def test_dry_run_write_check_and_idempotence(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            path = data / "entities" / "people" / "Fixture.json"
            path.parent.mkdir(parents=True)
            original = fixture()
            path.write_text(json.dumps(original), encoding="utf-8")
            initial_bytes = path.read_bytes()
            counts = tool.process(data, ("people",))
            self.assertEqual(counts["mode"], "dry_run")
            self.assertEqual(counts["total"]["records_changed"], 1)
            self.assertEqual(counts["total"]["description_rows_removed"], 2)
            self.assertEqual(path.read_bytes(), initial_bytes)
            with self.assertRaisesRegex(ValueError, "remains"):
                tool.process(data, ("people",), check=True)
            tool.process(data, ("people",), write=True)
            self.assertEqual(tool.process(data, ("people",), check=True)["total"]["records_changed"], 0)
            before = path.read_bytes()
            self.assertEqual(tool.process(data, ("people",), write=True)["total"]["records_changed"], 0)
            self.assertEqual(path.read_bytes(), before)

    def test_bad_input_aborts_before_any_write(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            d = data / "entities" / "places"
            d.mkdir(parents=True)
            good = d / "A.json"
            bad = d / "B.json"
            good.write_text(json.dumps(fixture()), encoding="utf-8")
            invalid = fixture()
            invalid["localizations"]["fra"]["descriptions"] = "not-an-array"
            bad.write_text(json.dumps(invalid), encoding="utf-8")
            original = good.read_bytes()
            with self.assertRaisesRegex(ValueError, "Unsupported descriptions type"):
                tool.process(data, ("places",), write=True)
            self.assertEqual(good.read_bytes(), original)

    def test_restricts_categories_and_write_check_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            for cats in (("keyterms",), ("unknown",), ("people", "people"), ()):
                with self.subTest(cats=cats), self.assertRaises(ValueError):
                    tool.process(data, cats)
            with self.assertRaises(ValueError):
                tool.process(data, ("people",), write=True, check=True)

    def test_existing_qualifiers_and_review_receipts_are_retained(self):
        path = ROOT / "data" / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        cleaned, rows, fields, holds = tool.prune_record(record)
        self.assertEqual((rows, fields, holds), (0, 0, False))
        self.assertEqual(cleaned, record)
        self.assertEqual(cleaned["bsi"]["identity_hint"],
                         record["bsi"]["identity_hint"])
        self.assertEqual(cleaned["explicit_instances"], record["explicit_instances"])


if __name__ == "__main__":
    unittest.main()
