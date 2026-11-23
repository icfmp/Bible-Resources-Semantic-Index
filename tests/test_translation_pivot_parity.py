"""Independent synthetic contract tests for original MACULA pivot parity auditing."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "translation_pivot_parity", ROOT / "scripts" / "audit_translation_pivot_parity.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def lock(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PivotParityAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source_paths = {}
        self.candidate_paths = {}
        self.pivot_paths = {}
        self.manifest = {
            "revision": "a" * 40,
            "groups": [],
            "inputs": [],
        }
        self.pivot_manifest = {"schema_version": 1, "sources": {}}
        self.receipt = {"upstream_revision": "a" * 40, "candidate_outputs": {}}
        for canon, stem, docid in (
            ("nt", "n40001001", "SBLGNT"),
            ("ot", "o01001001", "WLCM"),
        ):
            ids = [stem + f"{n:03d}" for n in (1, 2)]
            third = stem + "003"
            source = self.root / (canon + "_clear.tsv")
            pivot = self.root / (canon + "_macula.tsv")
            candidate_path = self.root / (canon + "_candidate.json")
            source.write_text(f"id\tlemma\n{ids[0]}\talpha\n{ids[1]}\tbeta\n", encoding="utf-8")
            pivot.write_text(f"xml:id\tlemma\n{ids[0]}\talpha\n{ids[1]}\tgamma\n{third}\textra\n",
                             encoding="utf-8")
            candidate = {
                "format": "brsi-translation-alignment-candidate",
                "schema_version": 1,
                "canon": canon,
                "upstream_revision": "a" * 40,
                "source_edition": docid,
                "by_source": {ids[0]: [0], ids[1]: [1]},
                "coverage": {"records": 2, "source_tokens": 2, "source_tokens_aligned": 2},
            }
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            self.manifest["groups"].append(
                {"canon": canon, "source": canon + "_source", "source_edition": docid})
            self.manifest["inputs"].append(
                {"key": canon + "_source", "sha256": lock(source)})
            self.pivot_manifest["sources"][canon] = {
                "revision": "b" * 40, "sha256": lock(pivot)}
            self.receipt["candidate_outputs"][canon] = {
                "sha256": lock(candidate_path), "coverage": {"records": 2}}
            self.source_paths[canon] = source
            self.pivot_paths[canon] = pivot
            self.candidate_paths[canon] = candidate_path

    def run_audit(self):
        return audit.audit(self.manifest, self.receipt, self.source_paths,
                           self.candidate_paths, self.pivot_manifest, self.pivot_paths)

    def test_exact_ids_and_lemmas_are_not_translation_certification(self):
        result = self.run_audit()
        for canon in ("nt", "ot"):
            row = result["canon_audits"][canon]
            self.assertEqual(row["source_tokens_clear_bible"], 2)
            self.assertEqual(row["source_tokens_brsi_macula"], 3)
            self.assertEqual(row["linked_ids_present_in_brsi_macula"], 2)
            self.assertEqual(row["linked_ids_absent_from_brsi_macula"], 0)
            self.assertEqual(row["linked_same_id_lemma_nfc_equal"], 1)
            self.assertEqual(row["linked_same_id_lemma_nfc_different"], 1)
            self.assertEqual(sum(row["mismatch_by_book"]["linked_id_lemma_different"].values()), 1)
            self.assertFalse(row["identity_certified"])
            self.assertFalse(row["contextual_senses_certified"])
            self.assertFalse(row["target_lsg_edition_certified"])

    def test_missing_original_id_is_reported_not_filled(self):
        with self.pivot_paths["nt"].open("a", encoding="utf-8") as f:
            f.write("n40001001004\tzeta\n")
        data = self.pivot_paths["nt"].read_text(encoding="utf-8")
        data = data.replace("n40001001002\tgamma\n", "")
        self.pivot_paths["nt"].write_text(data, encoding="utf-8")
        self.pivot_manifest["sources"]["nt"]["sha256"] = lock(self.pivot_paths["nt"])
        row = self.run_audit()["canon_audits"]["nt"]
        self.assertEqual(row["linked_ids_absent_from_brsi_macula"], 1)
        self.assertEqual(row["linked_ids_present_in_brsi_macula"], 1)

    def test_source_without_lemma_column_abstains_instead_of_inventing(self):
        path = self.source_paths["ot"]
        path.write_text(
            "id\\n" + "o01001001001\\n" + "o01001001002\\n",
            encoding="utf-8",
        )
        self.manifest["inputs"][1]["sha256"] = lock(path)
        summary = self.run_audit()["canon_audits"]["ot"]
        self.assertEqual(summary["linked_same_id_lemma_unavailable"], 2)
        self.assertEqual(summary["linked_same_id_lemma_nfc_equal"], 0)
        self.assertEqual(summary["linked_same_id_lemma_nfc_different"], 0)

    def test_upstream_byte_tampering_fails_closed(self):
        self.source_paths["ot"].write_text("id\tlemma\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA-256 changed"):
            self.run_audit()
        self.source_paths["ot"].write_text("id\tlemma\no01001001001\talpha\no01001001002\tbeta\n", encoding="utf-8")
        self.pivot_manifest["sources"]["nt"]["sha256"] = None
        with self.assertRaisesRegex(ValueError, "unlocked SHA-256"):
            self.run_audit()

    def test_duplicate_pivot_id_and_invalid_source_corpus_fail(self):
        with self.pivot_paths["nt"].open("a", encoding="utf-8") as f:
            f.write("n40001001001\tduplicate\n")
        self.pivot_manifest["sources"]["nt"]["sha256"] = lock(self.pivot_paths["nt"])
        with self.assertRaisesRegex(ValueError, "duplicated ID"):
            self.run_audit()
        self.pivot_paths["nt"].write_text("xml:id\tlemma\nn01001001001\twrong canon\n",
                                          encoding="utf-8")
        self.pivot_manifest["sources"]["nt"]["sha256"] = lock(self.pivot_paths["nt"])
        with self.assertRaisesRegex(ValueError, "outside expected corpus"):
            self.run_audit()


if __name__ == "__main__":
    unittest.main()
