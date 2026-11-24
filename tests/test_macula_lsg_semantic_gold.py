"""Independent bilingual human-gold validation without invented spans or approval."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_gold", ROOT / "scripts" /
    "validate_macula_lsg_semantic_gold.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def dossier():
    return {
        "reviewed_case_count": 0,
        "semantic_links_automatically_approved": 0,
        "model_proposals_included": False,
        "publication_authorized": False,
        "cases": [
            {"case_id": "a", "original_macula_id": "n40001001001",
             "source_verse_coordinate": "40001001",
             "source_cause": tool.sampler.STRATA[0],
             "evaluation_partition": "training"},
            {"case_id": "b", "original_macula_id": "o01001001001",
             "source_verse_coordinate": "01001001",
             "source_cause": tool.sampler.STRATA[1],
             "evaluation_partition": "calibration"},
            {"case_id": "c", "original_macula_id": "n40001002001",
             "source_verse_coordinate": "40001002",
             "source_cause": tool.sampler.STRATA[2],
             "evaluation_partition": "blind_validation"},
        ],
        "original_source_verses": {
            "40001001": [{"original_macula_id": "n40001001001", "present_in_correspondence_index": True},
                         {"original_macula_id": "n40001001002", "present_in_correspondence_index": True},
                         {"original_macula_id": "n40001001003", "present_in_correspondence_index": True}],
            "01001001": [{"original_macula_id": "o01001001001", "present_in_correspondence_index": True}],
            "40001002": [{"original_macula_id": "n40001002001", "present_in_correspondence_index": True}],
        },
        "exact_authored_french_verses": {
            "40001001": {
                "authorial_verse_present": True,
                "exact_words": [
                    {"word_id": f"40001001:{i}", "surface": word}
                    for i, word in enumerate(("Dieu", "nous", "appelle", "ici"), 1)]},
            "01001001": {
                "authorial_verse_present": True,
                "exact_words": [{"word_id": "01001001:1", "surface": "Dieu"}]},
            "40001002": {
                "authorial_verse_present": True,
                "exact_words": [{"word_id": "40001002:1", "surface": "Jésus"}]},
        },
    }


def review(case="a", reviewer="pastor-a", decision="phrase_span",
           source=None, spans=None):
    ids = {"a": ["n40001001001", "n40001001002"],
           "b": ["o01001001001"], "c": ["n40001002001"]}
    result = {
        "case_id": case,
        "reviewer_id": reviewer,
        "human_original_checked": True,
        "human_curated_french_checked": True,
        "decision": decision,
        "evidence": "Source morphology and authored French independently reviewed.",
        "original_macula_ids": source if source is not None else ids[case],
        "french_spans": spans if spans is not None else (
            [{"verse": "40001001", "word_ids": ["40001001:1", "40001001:2"]}]
            if decision == "phrase_span" else []),
    }
    if decision == "grammatical_unpaired":
        result["unpaired_function"] = "particle"
    if decision == "undetermined":
        result["undetermined_reason"] = "no_independent_evidence"
    return result


def submissions(reviews=None, adjudications=None):
    return {"schema_version": 1, "source_dossiers_gzip_sha256": "digest",
            "reviews": reviews or [], "adjudications": adjudications or []}


class HumanGoldTests(unittest.TestCase):
    def test_two_independent_humans_approve_private_phrase_gold_not_production(self):
        gold, report = tool.evaluate(
            dossier(), submissions([review(reviewer="alice"),
                                    review(reviewer="bob")]))
        self.assertEqual(report["human_gold_cases"], 1)
        self.assertEqual(report["total_human_submissions"], 2)
        self.assertEqual(report["counts"]["independently_agreed_cases"], 1)
        self.assertFalse(gold["production_approved"])
        self.assertFalse(gold["publication_authorized"])
        self.assertEqual(gold["adjudicated_cases"][0]["gold_research_decision"][
            "original_macula_ids"], [
            "n40001001001", "n40001001002"])
        self.assertFalse(gold["adjudicated_cases"][0]["automatic_production_approval"])
        self.assertEqual(report["automatic_production_approvals"], 0)

    def test_single_reviewer_and_missing_review_yields_no_gold(self):
        gold, report = tool.evaluate(dossier(), submissions([review()]))
        self.assertEqual(gold["human_gold_cases"], 0)
        self.assertEqual(report["human_gold_cases"], 0)
        self.assertEqual(report["counts"]["awaiting_independent_dual_review"], 3)

    def test_grammatical_unpaired_requires_no_french_highlight(self):
        r = review(case="b", reviewer="reader", decision="grammatical_unpaired")
        valid = tool.validated_review(r, dossier()["cases"][1], dossier())
        self.assertEqual(valid["french_spans"], [])
        self.assertEqual(valid["unpaired_function"], "particle")
        r["french_spans"] = [
            {"verse": "01001001", "word_ids": ["01001001:1"]}]
        with self.assertRaisesRegex(ValueError, "cannot force"):
            tool.validated_review(r, dossier()["cases"][1], dossier())

    def test_undetermined_is_a_real_negative_gold_decision(self):
        gold, report = tool.evaluate(
            dossier(), submissions([
                review(case="c", reviewer="one", decision="undetermined"),
                review(case="c", reviewer="two", decision="undetermined")]))
        self.assertEqual(report["counts"]["gold_undetermined"], 1)
        self.assertEqual(gold["adjudicated_cases"][0]["gold_research_decision"][
            "undetermined_reason"], "no_independent_evidence")

    def test_disagreement_requires_separate_human_adjudicator(self):
        contested = [
            review(reviewer="reader1"),
            review(reviewer="reader2", decision="undetermined",
                   source=["n40001001001"])]
        gold, report = tool.evaluate(dossier(), submissions(contested))
        self.assertEqual(gold["human_gold_cases"], 0)
        self.assertEqual(report["counts"]["unresolved_disputed_cases"], 1)
        adjudicator = review(reviewer="judge1")
        adjudicator["adjudication_rationale"] = (
            "Rechecked independent original grammar and authored text.")
        gold, report = tool.evaluate(
            dossier(), submissions(contested, [adjudicator]))
        self.assertEqual(report["counts"]["resolved_by_independent_adjudication"], 1)
        self.assertEqual(gold["human_gold_cases"], 1)
        adjudicator["reviewer_id"] = "reader1"
        with self.assertRaisesRegex(ValueError, "distinct third"):
            tool.evaluate(dossier(), submissions(contested, [adjudicator]))

    def test_original_span_must_be_contiguous_and_contain_reviewed_word(self):
        r = review(source=["n40001001001", "n40001001003"])
        with self.assertRaisesRegex(ValueError, "noncontiguous"):
            tool.validated_review(r, dossier()["cases"][0], dossier())
        r = review(source=["n40001001002"])
        with self.assertRaisesRegex(ValueError, "does not include"):
            tool.validated_review(r, dossier()["cases"][0], dossier())
        r = review(source=["n40001001001", "o01001001001"])
        with self.assertRaisesRegex(ValueError, "cross-verse"):
            tool.validated_review(r, dossier()["cases"][0], dossier())

    def test_exact_authored_french_word_boundaries_and_verse_lock(self):
        r = review(spans=[{"verse": "40001001",
                           "word_ids": ["40001001:1", "40001001:3"]}])
        with self.assertRaisesRegex(ValueError, "not contiguous"):
            tool.validated_review(r, dossier()["cases"][0], dossier())
        r = review(spans=[{"verse": "40001001",
                           "word_ids": ["40001001:5"]}])
        with self.assertRaisesRegex(ValueError, "not in exact"):
            tool.validated_review(r, dossier()["cases"][0], dossier())
        r = review(spans=[{"verse": "40001002",
                           "word_ids": ["40001002:1"]}])
        with self.assertRaisesRegex(ValueError, "cross-verse"):
            tool.validated_review(r, dossier()["cases"][0], dossier())
        r = review(spans=[{"verse": "40001001",
                           "word_ids": ["40001001:1", "40001001:2"]},
                          {"verse": "40001001",
                           "word_ids": ["40001001:2", "40001001:3"]}])
        with self.assertRaisesRegex(ValueError, "reused"):
            tool.validated_review(r, dossier()["cases"][0], dossier())

    def test_only_human_source_attested_reviews_are_eligible(self):
        r = review()
        r["human_original_checked"] = False
        with self.assertRaisesRegex(ValueError, "human"):
            tool.validated_review(r, dossier()["cases"][0], dossier())
        r = review()
        r["evidence"] = "guess"
        with self.assertRaisesRegex(ValueError, "substantive"):
            tool.validated_review(r, dossier()["cases"][0], dossier())
        r = review()
        r["decision"] = "automatic_semantic_match"
        with self.assertRaisesRegex(ValueError, "decision"):
            tool.validated_review(r, dossier()["cases"][0], dossier())

    def test_no_non_sample_or_duplicate_reviewer_or_unearned_adjudicator(self):
        r = review(case="a", reviewer="person1")
        with self.assertRaisesRegex(ValueError, "duplicate reviewer"):
            tool.evaluate(dossier(), submissions([r, r]))
        unknown = review(case="a")
        unknown["case_id"] = "not_sampled"
        with self.assertRaisesRegex(ValueError, "non-sampled"):
            tool.evaluate(dossier(), submissions([unknown]))
        adjudicator = review(reviewer="third")
        adjudicator["adjudication_rationale"] = "Independent third-party resolution notes."
        with self.assertRaisesRegex(ValueError, "fewer than two"):
            tool.evaluate(dossier(), submissions([r], [adjudicator]))
        with self.assertRaisesRegex(ValueError, "uncontested"):
            tool.evaluate(dossier(), submissions([
                review(reviewer="alice"), review(reviewer="bob")], [adjudicator]))

    def test_authentic_hebrew_extra_part_is_context_only_not_gold_identity(self):
        data = copy.deepcopy(dossier())
        data["original_source_verses"]["01001001"].append({
            "original_macula_id": "o01001001002",
            "present_in_correspondence_index": False})
        source = ["o01001001001", "o01001001002"]
        record = review(case="b", reviewer="person2",
                        decision="grammatical_unpaired", source=source)
        with self.assertRaisesRegex(ValueError, "absent from existing indexed"):
            tool.validated_review(record, data["cases"][1], data)

    def test_dossier_must_not_preexpose_machine_or_gold(self):
        data = copy.deepcopy(dossier())
        data["model_proposals_included"] = True
        with self.assertRaisesRegex(ValueError, "independent"):
            tool.evaluate(data, submissions())
        data = copy.deepcopy(dossier())
        data["reviewed_case_count"] = 1
        with self.assertRaisesRegex(ValueError, "prior gold"):
            tool.evaluate(data, submissions())


if __name__ == "__main__":
    unittest.main()
