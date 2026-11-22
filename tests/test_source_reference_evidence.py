"""Read-only audit covers every native reference and original-word witness."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_source_reference_evidence",
    ROOT / "scripts" / "audit_source_reference_evidence.py")
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class SourceReferenceEvidenceTests(unittest.TestCase):
    def test_separate_source_fields_and_distinguish_direct_from_indirect(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            directory = data / "entities" / "people"
            directory.mkdir(parents=True)
            rows = {
                "Explicit": {
                    "references": [], "key_references": ["01001001"],
                    "explicit_instances": {"wlc": [["o010010010011"]]},
                    "mentioned_in_bible": True,
                },
                "Indirect": {
                    "references": [], "key_references": ["01001001"],
                    "pronominal_referents": {"wlc": [["o010010010012"]]},
                    "mentioned_in_bible": True,
                },
                "OnlyKey": {
                    "references": [], "key_references": ["01001001"],
                    "mentioned_in_bible": True,
                },
                "NoEvidence": {
                    "references": [], "key_references": [],
                    "mentioned_in_bible": True,
                },
            }
            for name, fields in rows.items():
                record = {"id": "person:" + name, "type": "person",
                          "bsi": {"source_id": "person:" + name}, **fields}
                (directory / (name + ".json")).write_text(
                    json.dumps(record), encoding="utf-8")
            original = {p.name: p.read_bytes() for p in directory.iterdir()}
            result = audit_module.audit(data)
            self.assertEqual(result["counts"]["records_scanned"], 4)
            for kind in ("key_outside_general_with_exact_explicit_word",
                         "key_outside_general_with_indirect_word",
                         "key_outside_general_without_word",
                         "marked_biblical_no_general_no_explicit_has_indirect",
                         "marked_biblical_no_general_no_explicit_has_key",
                         "marked_biblical_no_general_no_explicit_no_key",
                         "explicit_word_verse_absent_general"):
                self.assertEqual(result["counts"][kind], 1, kind)
            self.assertEqual(
                original, {p.name: p.read_bytes() for p in directory.iterdir()})

    def test_current_dataset_is_classified_with_exact_record_pointers(self):
        report = audit_module.audit(ROOT / "data")
        counts = report["counts"]
        self.assertGreater(counts["records_scanned"], 5000)
        self.assertEqual(
            sum(counts.get(kind, 0) for kind in (
                "key_outside_general_with_exact_explicit_word",
                "key_outside_general_with_indirect_word",
                "key_outside_general_without_word")),
            sum(len(set(json.loads(p.read_text(encoding="utf-8"))["key_references"]) -
                    set(json.loads(p.read_text(encoding="utf-8"))["references"]))
                for p in (ROOT / "data" / "entities").glob("*/*.json")))
        self.assertEqual(
            counts.get("marked_biblical_no_general_no_explicit_no_key", 0)
            + counts.get("marked_biblical_no_general_no_explicit_has_key", 0)
            + counts.get("marked_biblical_no_general_no_explicit_has_indirect", 0),
            len([row for category, group in report["cases"].items()
                 if category.startswith("marked_biblical_no_general_")
                 for row in group]))
        print("BRSi_REFERENCE_AUDIT " + json.dumps(
            {"counts": counts, "counts_by_kind": report["counts_by_kind"],
             "samples": {key: val[:45] for key, val in report["samples"].items()}},
            ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
