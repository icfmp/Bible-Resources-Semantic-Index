"""Safety regressions for the private four-stratum MACULA-LSG review sampler."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "semantic_review_sampler",
    ROOT / "scripts" / "sample_macula_lsg_semantic_review.py")
sampler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sampler)


def fixture():
    rows, mapping, reasons = [], {}, {}
    for reason_no, reason in enumerate(sampler.STRATA):
        for n in range(12):
            # Each stratum covers two original books and 12 distinct verses.
            book = 1 + (n % 2) if reason_no % 2 else 40 + (n % 2)
            canon = "o" if book < 40 else "n"
            verse = f"{book:02d}{n + 1:03d}{reason_no + 1:03d}"
            source = f"{canon}{verse}001"
            reasons[source] = reason
            mapping[source] = [len(rows)]
            rows.append({"word_ids": []})
    return {
        "source_clear_bible_revision": "clear-pin",
        "source_aquifer_revision": "aquifer-pin",
        "curated_osis_sha256": "a" * 64,
        "by_original_macula_id": mapping,
        "unlinked_cause_by_original_macula_id": reasons,
        "rows": rows,
    }


def lock(index, sha="b" * 64):
    counts = {"nt": Counter(), "ot": Counter()}
    for source, reason in index["unlinked_cause_by_original_macula_id"].items():
        counts["nt" if source.startswith("n") else "ot"][reason] += 1
    return {
        "gzip_sha256": sha,
        "source_clear_bible_revision": index["source_clear_bible_revision"],
        "source_aquifer_revision": index["source_aquifer_revision"],
        "curated_osis_sha256": index["curated_osis_sha256"],
        "unlinked_source_cause_counts": {
            canon: dict(counts[canon]) for canon in ("nt", "ot")
        },
    }


class ReviewSamplerTests(unittest.TestCase):
    def test_exact_four_strata_and_distinct_original_ids(self):
        cases, population = sampler.select_cases(fixture(), per_stratum=6)
        self.assertEqual(len(cases), 24)
        self.assertEqual(len({x["original_macula_id"] for x in cases}), 24)
        self.assertEqual(len({x["source_verse_coordinate"] for x in cases}), 24)
        self.assertEqual(Counter(x["source_cause"] for x in cases),
                         {name: 6 for name in sampler.STRATA})
        self.assertEqual({x["review_status"] for x in cases}, {"unreviewed"})
        self.assertEqual(sum(x["total"] for x in population.values()), 48)
        self.assertTrue(all(len(population[name]["books"]) == 2
                            for name in sampler.STRATA))

    def test_reproducible_seeded_order_without_book_oversampling(self):
        data = fixture()
        a, _ = sampler.select_cases(data, per_stratum=6)
        b, _ = sampler.select_cases(data, per_stratum=6)
        self.assertEqual(a, b)
        self.assertNotEqual(
            sampler.rank(sampler.SEED, "n40001001001"),
            sampler.rank(sampler.SEED, "n40001001002"))

    def test_pinned_data_receipt_and_no_approved_links(self):
        index = fixture()
        expected = lock(index)
        raw, report = sampler.render(index, expected, expected["gzip_sha256"],
                                     per_stratum=6)
        document = json.loads(raw)
        self.assertEqual(document["case_count"], 24)
        self.assertEqual(document["reviewed_case_count"], 0)
        self.assertFalse(document["automatic_linguistic_approval"])
        self.assertFalse(document["publication_authorized"])
        self.assertTrue(report["overall_population_rate_requires_stratum_weights"])
        self.assertTrue(report["blind_evaluation_must_cluster_by_source_verse"])
        self.assertTrue(report["uniform_source_id_sampling_within_stratum"])
        self.assertEqual(report["private_unreviewed_cases_sha256"],
                         hashlib.sha256(raw).hexdigest())
        self.assertEqual(report["human_gold_cases"], 0)
        self.assertEqual(report["machine_proposals"], 0)
        self.assertTrue(all(case["manually_approved_french_spans"] is None and
                            case["explicit_unpaired_source"] is None and
                            not case["machine_candidate_approved"]
                            for case in document["cases"]))
        self.assertNotIn("Scripture", raw.decode("utf-8"))

    def test_original_source_sha_and_edition_pins_fail_closed(self):
        data = fixture()
        expected = lock(data)
        with self.assertRaisesRegex(ValueError, "checksum"):
            sampler.render(data, expected, "0"*64, per_stratum=6)
        modified = copy.deepcopy(data)
        modified["curated_osis_sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError, "edition"):
            sampler.render(modified, expected, expected["gzip_sha256"],
                           per_stratum=6)
        modified = copy.deepcopy(data)
        source = next(iter(modified["unlinked_cause_by_original_macula_id"]))
        modified["unlinked_cause_by_original_macula_id"][source] = sampler.STRATA[1]
        with self.assertRaisesRegex(ValueError, "census"):
            sampler.render(modified, expected, expected["gzip_sha256"],
                           per_stratum=6)

    def test_never_sample_already_linked_source(self):
        data = fixture()
        data["rows"][0]["word_ids"] = ["40001001:1"]
        with self.assertRaisesRegex(ValueError, "existing word"):
            sampler.select_cases(data, per_stratum=6)

    def test_reject_unknown_strata_or_bad_original_coordinates(self):
        data = fixture()
        source = next(iter(data["unlinked_cause_by_original_macula_id"]))
        data["unlinked_cause_by_original_macula_id"][source] = "other"
        with self.assertRaisesRegex(ValueError, "four strata"):
            sampler.select_cases(data, per_stratum=6)
        with self.assertRaisesRegex(ValueError, "invalid original"):
            sampler.coordinates("oINVALID")
        with self.assertRaisesRegex(ValueError, "positive"):
            sampler.select_cases(fixture(), per_stratum=0)

    def test_same_verse_tokens_stay_in_unbiased_original_id_sample(self):
        data = fixture()
        reason = sampler.STRATA[0]
        sources = [s for s, r in data["unlinked_cause_by_original_macula_id"].items()
                   if r == reason]
        first, second = sources[:2]
        shared_verse_other_token = first[:9] + "002"
        data["unlinked_cause_by_original_macula_id"].pop(second)
        data["unlinked_cause_by_original_macula_id"][shared_verse_other_token] = reason
        data["by_original_macula_id"][shared_verse_other_token] = (
            data["by_original_macula_id"].pop(second))
        cases, _ = sampler.select_cases(data, per_stratum=12)
        self.assertEqual(len(cases), 48)
        self.assertEqual(len({c["source_verse_coordinate"] for c in cases}), 47)
        self.assertIn(first, {c["original_macula_id"] for c in cases})
        self.assertIn(shared_verse_other_token,
                      {c["original_macula_id"] for c in cases})

    def test_not_enough_source_ids_fails_instead_of_repeating(self):
        with self.assertRaisesRegex(ValueError, "cannot fulfill"):
            sampler.select_cases(fixture(), per_stratum=20)


if __name__ == "__main__":
    unittest.main()
