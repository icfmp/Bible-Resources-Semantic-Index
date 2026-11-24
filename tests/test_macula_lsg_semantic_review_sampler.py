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
    def test_exact_four_strata_and_distinct_verses(self):
        cases, population = sampler.select_cases(fixture(), per_stratum=6)
        self.assertEqual(len(cases), 24)
        self.assertEqual(len({x["original_macula_id"] for x in cases}), 24)
        self.assertEqual(len({x["source_verse_coordinate"] for x in cases}), 24)
        self.assertEqual(Counter(x["source_cause"] for x in cases),
                         {name: 6 for name in sampler.STRATA})
        self.assertEqual({x["review_status"] for x in cases}, {"unreviewed"})
        self.assertEqual(sum(x["total"] for x in population.values()), 48)
        self.assertTrue(all(len(set(population[name]["books"])) == 2
                            for name in sampler.STRATA))

    def test_reproducible_seeded_order_and_each_book_covered(self):
        data = fixture()
        a, _ = sampler.select_cases(data, per_stratum=6)
        b, _ = sampler.select_cases(data, per_stratum=6)
        self.assertEqual(a, b)
        for reason in sampler.STRATA:
            self.assertEqual(len({x["book_code"] for x in a
                                  if x["source_cause"] == reason}), 2)
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
        self.assertFalse(report["population_error_rate_estimable_without_weights"])
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

    def test_no_artificial_fill_when_unique_verse_sample_insufficient(self):
        data = fixture()
        reason = sampler.STRATA[0]
        sources = [s for s, r in data["unlinked_cause_by_original_macula_id"].items()
                   if r == reason]
        # Many distinct original tokens within the same verse are not many
        # independent review observations; this must not silently fill quota.
        shared = sources[0][1:9]
        for source in sources[1:]:
            new_source = source[0] + shared + source[9:]
            # Token IDs must remain distinct (a second part/source ordinal).
            if new_source in data["unlinked_cause_by_original_macula_id"]:
                continue
        with self.assertRaisesRegex(ValueError, "cannot fulfill"):
            sampler.select_cases(data, per_stratum=20)


if __name__ == "__main__":
    unittest.main()
