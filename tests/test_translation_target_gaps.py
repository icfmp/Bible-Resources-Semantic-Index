"""Synthetic negative and positive controls for source-locked translation gap triage."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "audit_translation_target_gaps.py"
spec = importlib.util.spec_from_file_location("brsi_gap_audit", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TranslationGapAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.candidates = self.root / "candidates"
        self.candidates.mkdir()
        self.revision = "a" * 40
        self.docs = {
            "nt": {
                "format": "brsi-translation-alignment-candidate", "canon": "nt",
                "upstream_revision": self.revision,
                "coverage": {"target_census_complete": True,
                             "problem_target_token_unattested": 4, "records": 4},
                "records": [
                    {"source_lookup_ids": ["n40001001001"], "target_lookup_ids": ["40001001001"],
                     "problems": ["target_token_unattested"]},
                    {"source_lookup_ids": ["n40001001002"], "target_lookup_ids": ["40001001006"],
                     "problems": ["target_token_unattested"]},
                    {"source_lookup_ids": ["n40001002001"], "target_lookup_ids": ["40001001003"],
                     "problems": ["target_token_unattested"]},
                    {"source_lookup_ids": ["n40001003001"], "target_lookup_ids": ["40001003001"],
                     "problems": ["target_token_unattested"]},
                ],
            },
            "ot": {
                "format": "brsi-translation-alignment-candidate", "canon": "ot",
                "upstream_revision": self.revision,
                "coverage": {"target_census_complete": False,
                             "problem_cross_verse_selector": 2, "records": 2},
                "records": [
                    {"source_lookup_ids": ["o01001001001"], "target_lookup_ids": ["01001002001"],
                     "problems": ["cross_verse_selector", "target_census_unavailable"]},
                    {"source_lookup_ids": ["o01001003001"], "target_lookup_ids": ["01002001001"],
                     "problems": ["cross_verse_selector", "target_census_unavailable"]},
                ],
            },
        }
        target_rows = {
            "nt": "id\tword\n40001001002\tone\n40001001005\ttwo\n40001002001\tthree\n",
            "ot": "id\tword\n",
        }
        self.manifest = {"schema_version": 1, "revision": self.revision,
                         "groups": [], "inputs": []}
        self.receipt = {"upstream_revision": self.revision, "publication_approved": False,
                        "candidate_outputs": {}}
        for canon, body in target_rows.items():
            path = self.root / f"{canon}.tsv"
            raw = body.encode("utf-8")
            path.write_bytes(raw)
            self.manifest["inputs"].append({"key": canon + "_target", "path": path.name,
                                             "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
            self.manifest["groups"].append({"canon": canon, "target": canon + "_target"})
            self.write_candidate(canon)
        self.write_receipt()

    def write_candidate(self, canon):
        raw = json.dumps(self.docs[canon]).encode("utf-8")
        (self.candidates / (canon + ".json")).write_bytes(raw)
        self.receipt["candidate_outputs"][canon] = {"sha256": hashlib.sha256(raw).hexdigest()}

    def write_receipt(self):
        (self.candidates / "receipt.json").write_text(json.dumps(self.receipt), encoding="utf-8")

    def run_audit(self):
        return module.audit(self.candidates, self.manifest, self.root)

    def test_descriptive_groups_never_suggest_token_repairs(self):
        report = self.run_audit()
        nt = report["groups"]["nt"]
        self.assertEqual(nt["unattested_target_records"], 4)
        self.assertEqual(nt["unattested_target_classes"], {
            "above_target_verse_span": 1, "below_target_verse_span": 1,
            "gap_within_target_verse_span": 1, "target_verse_absent": 1,
        })
        self.assertEqual(nt["unattested_target_by_book"], {"40": 4})
        self.assertEqual(nt["unattested_target_distinct_verses"], 2)
        self.assertEqual(nt["unattested_targets_per_verse"], {"1": 1, "3": 1})
        self.assertEqual(nt["above_target_span_ordinal_gaps"], {"word_ordinal_+1": 1})
        ot = report["groups"]["ot"]
        self.assertFalse(ot["target_inventory_present"])
        self.assertEqual(ot["cross_verse_classes"], {
            "different_chapter": 1, "different_verse_same_chapter": 1,
        })
        self.assertEqual(ot["same_chapter_verse_deltas"], {"+1": 1})
        self.assertEqual(ot["distinct_cross_verse_pairs"], 2)
        self.assertEqual(ot["versification_corrections_inferred"], 0)
        self.assertFalse(report["publication_approved"])
        self.assertFalse(report["edition_or_word_identity_certified"])
        self.assertNotIn("one", json.dumps(report))

    def test_subword_part_is_not_mistaken_for_a_word_ordinal(self):
        self.docs["nt"]["records"][1]["target_lookup_ids"] = ["400010010051"]
        self.write_candidate("nt")
        self.write_receipt()
        result = self.run_audit()["groups"]["nt"]
        self.assertEqual(result["above_target_span_ordinal_gaps"], {"subword_part_+1": 1})

    def test_reject_altered_original_witness(self):
        (self.root / "nt.tsv").write_text("id\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from manifest"):
            self.run_audit()

    def test_reject_altered_candidate(self):
        self.docs["nt"]["records"][0]["target_lookup_ids"] = ["40001001005"]
        (self.candidates / "nt.json").write_text(json.dumps(self.docs["nt"]))
        with self.assertRaisesRegex(ValueError, "candidate JSON differs"):
            self.run_audit()

    def test_reject_contradictory_problem_counter(self):
        self.docs["ot"]["coverage"]["problem_cross_verse_selector"] = 1
        self.write_candidate("ot")
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, "cross-verse count disagrees"):
            self.run_audit()

    def test_reject_false_publication_claim(self):
        self.receipt["publication_approved"] = True
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, "revision mismatch or public receipt"):
            self.run_audit()

    def test_reject_missing_target_id_audit_without_inventory(self):
        self.docs["ot"]["records"][0]["problems"].append("target_token_unattested")
        self.docs["ot"]["coverage"]["problem_target_token_unattested"] = 1
        self.write_candidate("ot")
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, "missing-target claim without inventory"):
            self.run_audit()


if __name__ == "__main__":
    unittest.main()
