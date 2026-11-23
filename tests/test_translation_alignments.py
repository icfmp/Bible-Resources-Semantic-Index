"""Synthetic, source-independent translation-alignment regression tests."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brsi_translation_alignments",
                                              ROOT / "scripts" / "build_translation_alignments.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sha_git(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class TranslationAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = {
            "schema_version": 1,
            "revision": "a" * 40,
            "target_edition": "synthetic LSG not real data",
            "groups": [
                {"canon": "nt", "source": "ns", "target": "nt", "alignment": "na",
                 "source_edition": "synthetic Greek", "source_docid": "SBLGNT", "target_docid": "LSG"},
                {"canon": "ot", "source": "os", "target": "ot", "alignment": "oa",
                 "source_edition": "synthetic Hebrew", "source_docid": "WLCM", "target_docid": "LSG"},
            ],
            "inputs": [],
        }
        self.payloads = {
            "ns": "id\ttext\nn40001001001\t\u03b1\nn40001001002\t\u03b2\n",
            "nt": "id\ttext\n40001001001\ta\n40001001002\tb\n40001001003\tc\n",
            "os": "id\ttext\no010010010011\t\u05d0\no010010010021\t\u05d1\n",
            "ot": "id\ttext\n",
            "na": {
                "meta": {"origin": "manual"}, "type": "translation",
                "documents": [{"docid": "SBLGNT"}, {"docid": "LSG"}],
                "roles": ["source", "target"],
                "records": [
                    {"meta": {"id": "explicit-1"}, "source": ["n40001001001"],
                     "target": ["40001001001"]},
                    {"source": ["n40001001002", "n40001001001"],
                     "target": ["40001001002", "40001001003"]},
                ],
            },
            "oa": {
                "meta": {"origin": "manual"}, "type": "translation",
                "documents": [{"docid": "WLCM"}, {"docid": "LSG"}],
                "roles": ["source", "target"],
                "records": [
                    {"source": ["o010010010011"], "target": ["01001001001"]},
                    {"source": [], "target": ["01001001002"]},
                ],
            },
        }
        for key, payload in self.payloads.items():
            raw = (json.dumps(payload, ensure_ascii=False).encode("utf-8")
                   if isinstance(payload, dict) else payload.encode("utf-8"))
            (self.root / key).write_bytes(raw)
            self.manifest["inputs"].append({
                "key": key, "path": key, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "git_blob_sha": sha_git(raw),
            })
        self.corrections = {"schema_version": 1, "corrections": []}

    def build(self):
        return module.build(self.manifest, self.corrections, self.root)

    def test_complete_groups_preserve_many_to_many_and_raw_ids(self):
        indexes, receipts = self.build()
        nt, ot = indexes["nt"], indexes["ot"]
        self.assertEqual(nt["coverage"]["records"], 2)
        self.assertEqual(nt["coverage"]["topology_many_to_many"], 1)
        self.assertEqual(nt["coverage"]["topology_one_to_one"], 1)
        self.assertEqual(nt["coverage"]["source_attested"], 2)
        self.assertEqual(nt["coverage"]["source_tokens_multiple_groups"], 1)
        self.assertEqual(nt["records"][1]["source_ids_original"],
                         ["n40001001002", "n40001001001"])
        self.assertEqual(nt["by_source"]["n40001001001"], [0, 1])
        self.assertEqual(nt["original_group_meta"], {"origin": "manual"})
        self.assertEqual(nt["records"][0]["original_record_meta"], {"id": "explicit-1"})
        self.assertEqual(nt["coverage"]["target_tokens_unaligned"], 0)
        self.assertEqual(ot["coverage"]["target_unverified"], 1)
        self.assertEqual(ot["coverage"]["unresolved"], 1)
        self.assertIsNone(ot["coverage"]["target_tokens"])
        self.assertIn("target_census_unavailable", ot["records"][0]["problems"])
        self.assertEqual(ot["problem_counts_by_book"]["target_census_unavailable"], {"01": 2})
        self.assertFalse(ot["records"][0]["independently_reviewed"])
        self.assertNotIn("\u03b1", json.dumps(nt, ensure_ascii=False))
        self.assertNotIn("\u05d0", json.dumps(ot, ensure_ascii=False))
        self.assertIn("sha256", receipts["na"])

    def test_missing_or_crossverse_selectors_do_not_generate_guesses(self):
        group = self.payloads["na"]
        group["records"][0]["target"] = ["40001002001"]
        (self.root / "na").write_text(json.dumps(group), encoding="utf-8")
        self.relock("na")
        result = self.build()[0]["nt"]
        self.assertEqual(result["records"][0]["validation"], "unresolved")
        self.assertIn("cross_verse_selector", result["records"][0]["problems"])
        self.assertIn("target_token_unattested", result["records"][0]["problems"])
        self.assertEqual(result["records"][0]["target_lookup_ids"], ["40001002001"])

    def test_detect_invalid_source_without_forging_identity(self):
        self.payloads["na"]["records"][0]["source"] = ["n01001001001"]
        (self.root / "na").write_text(json.dumps(self.payloads["na"]), encoding="utf-8")
        self.relock("na")
        row = self.build()[0]["nt"]["records"][0]
        self.assertIn("missing_or_invalid_selector", row["problems"])
        self.assertEqual(row["source_ids_original"], ["n01001001001"])
        self.assertEqual(row["source_lookup_ids"], [None])

    def test_gzip_candidate_is_reproducible_and_lossless(self):
        raw = module.canonical_json(self.build()[0]["nt"])
        first, second = module.gzip_payload(raw), module.gzip_payload(raw)
        self.assertEqual(first, second)
        self.assertEqual(gzip.decompress(first), raw)
        self.assertEqual(first[4:8], b"\\x00" * 4)

    def test_reject_swapped_documents_and_ambiguous_roles(self):
        self.payloads["na"]["documents"][1]["docid"] = "AnotherTranslation"
        (self.root / "na").write_text(json.dumps(self.payloads["na"]), encoding="utf-8")
        self.relock("na")
        with self.assertRaisesRegex(ValueError, "document editions disagree"):
            self.build()
        self.payloads["na"]["documents"][1]["docid"] = "LSG"
        self.payloads["na"]["roles"] = ["target", "source"]
        (self.root / "na").write_text(json.dumps(self.payloads["na"]), encoding="utf-8")
        self.relock("na")
        with self.assertRaisesRegex(ValueError, "roles absent, reversed"):
            self.build()

    def test_reject_source_tamper_and_duplicate_json_fields(self):
        (self.root / "ns").write_text("id\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "input size differs"):
            self.build()
        self.assertRaisesRegex(ValueError, "duplicate JSON key",
                               lambda: module.strict_object([("a", 1), ("a", 2)]))

    def test_require_independent_sha256_pin(self):
        self.manifest["inputs"][0]["sha256"] = None
        with self.assertRaisesRegex(ValueError, "missing or malformed pinned SHA-256"):
            self.build()

    def test_reject_duplicate_source_tokens(self):
        self.payloads["ns"] += "n40001001001\tduplicate\n"
        (self.root / "ns").write_text(self.payloads["ns"], encoding="utf-8")
        self.relock("ns")
        with self.assertRaisesRegex(ValueError, "duplicate token ID"):
            self.build()

    def test_fail_closed_correction_ledger_without_rewriting_original(self):
        self.corrections["corrections"] = [{
            "locator": "nt:0",
            "expected": {"source": ["n40001001001"], "target": ["40001001001"]},
            "replacement": {"source": ["n40001001001"], "target": ["40001001002"]},
            "evidence": ["Synthetic independent printed witness, not a real correction"],
        }]
        row = self.build()[0]["nt"]["records"][0]
        self.assertEqual(row["target_ids_original"], ["40001001001"])
        self.assertEqual(row["target_lookup_ids"], ["40001001002"])
        self.assertTrue(row["correction_applied"])
        self.corrections["corrections"][0]["expected"]["target"] = ["bogus"]
        with self.assertRaisesRegex(ValueError, "original witness changed"):
            self.build()

    def test_reject_correction_without_evidence_or_missing_locator(self):
        self.corrections["corrections"] = [{
            "locator": "ot:1",
            "expected": {"source": [], "target": ["01001001002"]},
            "replacement": {"source": ["o010010010011"], "target": ["01001001002"]},
            "evidence": [],
        }]
        with self.assertRaisesRegex(ValueError, "missing independently reviewed"):
            self.build()
        self.corrections["corrections"][0]["evidence"] = ["Synthetic witness"]
        self.corrections["corrections"][0]["locator"] = "ot:99999"
        with self.assertRaisesRegex(ValueError, "unused corrections"):
            self.build()

    def test_invalid_token_ids_and_duplicate_selectors(self):
        for token in ("n40001000001", "n40000001001", "n99001001001",
                      "n40001001000", "bad"):
            self.assertIsNone(module.corpus_id(token, "nt", True), token)
        self.assertEqual(module.corpus_id("40001001001", "nt", True),
                         "n40001001001")
        self.assertEqual(module.corpus_id("o010010010011", "ot", True),
                         "o010010010011")
        with self.assertRaisesRegex(ValueError, "duplicate selector"):
            module.selectors(["n40001001001", "n40001001001"], "nt", True)

    def relock(self, key):
        raw = (self.root / key).read_bytes()
        item = next(x for x in self.manifest["inputs"] if x["key"] == key)
        item["size"] = len(raw)
        item["sha256"] = hashlib.sha256(raw).hexdigest()
        item["git_blob_sha"] = sha_git(raw)


if __name__ == "__main__":
    unittest.main()
