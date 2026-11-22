"""Only unreviewed, redundant non-English display labels may be discarded."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brsi_prune_names",
    ROOT / "scripts" / "prune_nonworking_labels.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def fixture():
    return {
        "id": "person:Fixture", "type": "person",
        "references": ["41015040"], "key_references": ["41015040"],
        "explicit_instances": {"sblgnt": [["n41015040004"]]},
        "father": "person:Ancestor",
        "bsi": {
            "canonical_id": "person:Fixture",
            "source_id": "person:Fixture",
            "source_sha256": "a" * 64,
            "identity_hint": {"name": "A", "qualifier": "mother of B",
                              "language": "eng", "evidence_references": ["41015040"],
                              "review_status": "editorially_reviewed"},
            "inherited_localizations": {
                "status": "withheld_pending_review",
                "fields": ["eng.alternate_labels"], "source": "acai", "reason": "Review"},
        },
        "localizations": {
            "eng": {"preferred_label": "A", "alternate_labels": ["Other name"]},
            "fra": {"preferred_label": "B"},
            "spa": {"preferred_label": "C"},
        },
    }


class PruneLocaleTests(unittest.TestCase):
    def test_only_redundant_names_removed_and_id_links_retained(self):
        original = fixture()
        before = copy.deepcopy(original)
        cleaned, removed = tool.prune_record(original)
        self.assertEqual(removed, 2)
        self.assertEqual(original, before)
        self.assertEqual(list(cleaned["localizations"]), ["eng"])
        expected = copy.deepcopy(original)
        del expected["localizations"]["fra"]
        del expected["localizations"]["spa"]
        self.assertEqual(cleaned, expected)
        self.assertEqual(cleaned["bsi"]["identity_hint"]["qualifier"],
                         "mother of B")

    def test_unknown_nonenglish_fields_or_holds_stop_pruning(self):
        for update in (
            lambda r: r["localizations"]["fra"].update({"alternate_labels": ["Alias"]}),
            lambda r: r["localizations"]["fra"].update({"description": "No"}),
            lambda r: r["localizations"]["fra"].update({"preferred_label": ""}),
            lambda r: r["bsi"]["inherited_localizations"]["fields"].append("fra.preferred_label"),
            lambda r: r["localizations"]["eng"].pop("preferred_label"),
        ):
            record = fixture()
            update(record)
            with self.assertRaises(ValueError):
                tool.prune_record(record)

    def test_real_mary_record_has_a_distinct_english_hint(self):
        record = json.loads((ROOT / "data/entities/people/Mary.2.json")
                            .read_text(encoding="utf-8"))
        before = copy.deepcopy(record)
        cleaned, removed = tool.prune_record(record)
        self.assertEqual(removed, 18)
        self.assertEqual(list(cleaned["localizations"]), ["eng"])
        self.assertEqual(cleaned["bsi"]["identity_hint"],
                         before["bsi"]["identity_hint"])
        self.assertEqual(record, before)

    def test_dry_run_check_write_and_bad_source_abort(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / "entities" / "people"
            root.mkdir(parents=True)
            a = root / "A.json"
            b = root / "B.json"
            a.write_text(json.dumps(fixture()), encoding="utf-8")
            corrupted = fixture()
            corrupted["localizations"]["fra"]["unexpected"] = "Value"
            b.write_text(json.dumps(corrupted), encoding="utf-8")
            before = a.read_bytes()
            with self.assertRaises(ValueError):
                tool.process(base, ("people",), write=True)
            self.assertEqual(before, a.read_bytes())
            b.unlink()
            self.assertEqual(tool.process(base, ("people",))["totals"]["changed"], 1)
            with self.assertRaises(ValueError):
                tool.process(base, ("people",), check=True)
            tool.process(base, ("people",), write=True)
            self.assertEqual(tool.process(base, ("people",), check=True)["totals"]["changed"], 0)
            self.assertEqual(list(json.loads(a.read_text())["localizations"]), ["eng"])

    def test_never_prunes_restricted_keyterms(self):
        with self.assertRaisesRegex(ValueError, "Key Terms"):
            tool.process(ROOT / "data", ("keyterms",))


if __name__ == "__main__":
    unittest.main()
