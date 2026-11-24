"""Exact original/authorial verse reviewer dossiers must not create gold."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_dossiers", ROOT / "scripts" /
    "build_macula_lsg_semantic_review_dossiers.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def sample_fixture():
    indexed = {"by_original_macula_id": {}, "unlinked_cause_by_original_macula_id": {},
               "rows": []}
    cases, original = [], {"nt": {}, "ot": {}}
    verses = ("40001001", "40001002", "01001001", "01001002")
    for no, reason in enumerate(tool.sampler.STRATA):
        verse = verses[no]
        canon = "nt" if no < 2 else "ot"
        prefix = "n" if canon == "nt" else "o"
        original[canon][verse] = []
        for j in range(500):
            source = prefix + verse + f"{j + 1:03d}"
            row = {"word_ids": [], "original_clear_bible_target_ids": []}
            if no == 2 and j == 0:
                row["original_clear_bible_target_ids"] = ["01001002001"]
            indexed["rows"].append(row)
            indexed["by_original_macula_id"][source] = [len(indexed["rows"]) - 1]
            indexed["unlinked_cause_by_original_macula_id"][source] = reason
            original[canon][verse].append({
                "original_macula_id": source, "source_form": "λέγω",
                "lemma": "λέγω", "morphology": None, "part_of_speech": "V"})
            cases.append({
                "case_id": f"case-{no:02d}-{j:03d}",
                "original_macula_id": source, "source_cause": reason,
                "canon": canon, "book_code": verse[:2],
                "source_verse_coordinate": verse,
            })
    return indexed, cases, original, {
        "source_clear_bible_revision": "clear",
        "source_aquifer_revision": "aquifer",
        "curated_osis_sha256": "a" * 64,
        "gzip_sha256": "b" * 64,
    }


class DossierTests(unittest.TestCase):
    def test_verse_cluster_split_is_deterministic_and_nonoverlapping(self):
        verses = ("40001001", "40001002", "01001001", "01001002")
        self.assertTrue(all(tool.partition(verse) == tool.partition(verse)
                            for verse in verses))
        with self.assertRaisesRegex(ValueError, "invalid verse"):
            tool.partition("Gen.1.1")

    def test_review_case_context_exact_edition_and_unapproved(self):
        index, cases, original, lock = sample_fixture()
        authored = {verse: "Dieu est bon." for verse in
                    ("40001001", "40001002", "01001001", "01001002")}
        prior = copy.deepcopy(index)
        data, receipt = tool.build_dossiers(
            index, cases, original["nt"], original["ot"], authored,
            source_pin=lock, sample_sha="private-sample")
        self.assertEqual(index, prior)
        self.assertEqual(len(data["cases"]), 2000)
        self.assertEqual(len(data["original_source_verses"]), 4)
        self.assertEqual(len(data["exact_authored_french_verses"]), 4)
        self.assertEqual(receipt["sample_original_macula_ids"], 2000)
        self.assertEqual(receipt["original_source_verses"], 4)
        self.assertEqual(receipt["original_target_verse_disagreement_cases"], 1)
        self.assertEqual(receipt["missing_authored_same_coordinate_verses"], 0)
        self.assertEqual(data["reviewed_case_count"], 0)
        self.assertEqual(receipt["human_gold_reviewed_cases"], 0)
        self.assertEqual(receipt["automatic_approved_word_links"], 0)
        self.assertFalse(data["model_proposals_included"])
        self.assertFalse(data["publication_authorized"])
        self.assertTrue(all(not x["machine_candidate_visible_to_reviewers"] and
                            x["review_decision"] is None for x in data["cases"]))
        for case in data["cases"]:
            self.assertEqual(case["evaluation_partition"],
                             tool.partition(case["source_verse_coordinate"]))
            source_verse = case["source_verse_coordinate"]
            self.assertIn(case["original_macula_id"], {
                row["original_macula_id"]
                for row in data["original_source_verses"][source_verse]})
        words = data["exact_authored_french_verses"]["40001001"]["exact_words"]
        self.assertEqual([w["word_id"] for w in words],
                         ["40001001:1", "40001001:2", "40001001:3"])
        self.assertEqual([w["surface"] for w in words],
                         ["Dieu", "est", "bon"])
        self.assertEqual(
            data["exact_authored_french_verses"]["40001001"]["nfc_verse"],
            authored["40001001"])
        self.assertTrue(all(
            receipt["partition_by_canon"][split]["nt"] +
            receipt["partition_by_canon"][split].get("ot", 0) ==
            receipt["source_verse_cluster_partition_counts"][split]
            for split in receipt["source_verse_cluster_partition_counts"]
            if "nt" in receipt["partition_by_canon"][split]))

    def test_missing_exact_source_verse_is_not_filled_by_verse_guess(self):
        index, cases, original, lock = sample_fixture()
        authored = {verse: "Dieu dit." for verse in
                    ("40001001", "40001002", "01001001")}
        data, receipt = tool.build_dossiers(
            index, cases, original["nt"], original["ot"], authored,
            source_pin=lock, sample_sha="sample")
        self.assertEqual(receipt["missing_authored_same_coordinate_verses"], 500)
        self.assertFalse(
            data["exact_authored_french_verses"]["01001002"]["authorial_verse_present"])
        self.assertIsNone(
            data["exact_authored_french_verses"]["01001002"]["nfc_verse"])

    def test_non_sample_original_id_and_modified_cause_fail_closed(self):
        index, cases, original, lock = sample_fixture()
        wrong = copy.deepcopy(cases)
        wrong[0]["source_cause"] = tool.sampler.STRATA[-1]
        with self.assertRaisesRegex(ValueError, "identity"):
            tool.build_dossiers(
                index, wrong, original["nt"], original["ot"], {},
                source_pin=lock, sample_sha="sample")
        modified = copy.deepcopy(original)
        modified["nt"]["40001001"].pop(0)
        with self.assertRaisesRegex(ValueError, "absent/duplicated"):
            tool.build_dossiers(
                index, cases, modified["nt"], modified["ot"], {},
                source_pin=lock, sample_sha="sample")

    def test_repeated_case_id_and_overlap_fail(self):
        index, cases, original, lock = sample_fixture()
        bad = copy.deepcopy(cases)
        bad[0]["case_id"] = bad[1]["case_id"]
        with self.assertRaisesRegex(ValueError, "reused"):
            tool.build_dossiers(index, bad, original["nt"], original["ot"], {},
                                source_pin=lock, sample_sha="sample")
        bad = cases[:-1]
        with self.assertRaisesRegex(ValueError, "count"):
            tool.build_dossiers(index, bad, original["nt"], original["ot"], {},
                                source_pin=lock, sample_sha="sample")

    def test_exact_macula_tsv_fields_hash_and_original_source_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.tsv"
            raw = ("xml:id\tlemma\ttext\tsp\tmorph\n"
                   "40001001001\tθεός\tθεός\tN\tN-NSM\n"
                   "40001001002\tλέγω\tλέγει\tV\tV-PAI-3S\n")
            path.write_text(raw, encoding="utf-8")
            correct = hashlib.sha256(path.read_bytes()).hexdigest()
            d, receipt = tool.selected_original_context(
                path, "nt", correct, {"40001001"}, expected_count=2)
            self.assertEqual(receipt["original_tokens_scanned"], 2)
            self.assertEqual(receipt["source_form_column"], "text")
            self.assertEqual(receipt["part_of_speech_column"], "sp")
            self.assertEqual(d["40001001"][0]["source_form"], "θεός")
            self.assertEqual(d["40001001"][1]["morphology"], "V-PAI-3S")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                tool.selected_original_context(
                    path, "nt", "0"*64, {"40001001"}, expected_count=2)
            with self.assertRaisesRegex(ValueError, "census"):
                tool.selected_original_context(
                    path, "nt", correct, {"40001001"}, expected_count=3)
            path.write_text(raw + "40001001001\tθεός\tθεός\tN\tN-NSM\n",
                            encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "duplicate"):
                tool.selected_original_context(
                    path, "nt", digest, {"40001001"}, expected_count=3)

    def test_private_gzip_reproducible_and_never_upload_text(self):
        doc = {"original_source_verses":{"40001001":[{"source_form":"θεός"}]},
               "exact_authored_french_verses":{"40001001":{"nfc_verse":"Dieu"}}}
        one = tool.private_gzip(doc)
        self.assertEqual(one, tool.private_gzip(doc))
        self.assertEqual(json.loads(__import__("gzip").decompress(one)), doc)
        self.assertNotIn(b"Dieu", one)


if __name__ == "__main__":
    unittest.main()
