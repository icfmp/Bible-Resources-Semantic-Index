"""Whole-verse semantic preparation, clause grouping and fail-closed validation."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_full_verse_semantic", ROOT / "scripts" /
    "prepare_macula_lsg_verse_semantic_pilot.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def fixture():
    """2,000 synthetic cases over 200 independent source verses, not real Bible."""
    tokens_by_verse = {}
    french_by_verse = {}
    cases = []
    for canon, book in (("nt", "63"), ("ot", "01")):
        for ordinal in range(1, 101):
            verse = f"{book}001{ordinal:03d}"
            sources = [f"{'n' if canon == 'nt' else 'o'}{verse}w{i:02d}"
                       for i in range(1, 11)]
            tokens_by_verse[verse] = [
                {"original_macula_id": s, "source_form": f"form-{i}",
                 "lemma": f"lemma-{i}", "morphology": "morph",
                 "part_of_speech": None,
                 "present_in_correspondence_index": True}
                for i, s in enumerate(sources, 1)]
            french_by_verse[verse] = {
                "authorial_verse_present": True,
                "source_coordinate": verse,
                "nfc_verse": "La phrase parle de son sujet",
                "exact_words": [{"word_id": f"{verse}:{i}", "surface": surface,
                                 "nfc_start_codepoint": i * 3,
                                 "nfc_end_codepoint": i * 3 + len(surface)}
                                for i, surface in enumerate(
                                    ("La", "phrase", "parle", "de", "son", "sujet"), 1)],
                "context_neighbors": {},
            }
            for i, s in enumerate(sources):
                cases.append({
                    "case_id": f"case-{canon}-{ordinal}-{i}",
                    "original_macula_id": s,
                    "source_verse_coordinate": verse, "context_key": verse,
                    "evaluation_partition": "training", "canon": canon,
                    "source_cause": "synthetic_unresolved_original_id",
                    "original_target_verse_disagreement": False,
                })
    return {
        "cases": cases, "original_source_verses": tokens_by_verse,
        "exact_authored_french_verses": french_by_verse,
        "source_index_gzip_sha256": "a" * 64,
        "authored_french_osis_sha256": "b" * 64,
        "reviewed_case_count": 0, "model_proposals_included": False,
        "semantic_links_automatically_approved": 0, "publication_authorized": False,
    }


def valid_response(pilot):
    results = []
    for task in pilot["tasks"]:
        src = [row["original_macula_id"]
               for row in task["original_tokens_in_source_order"]]
        words = [w["word_id"] for w in task["authored_french"]["exact_words"]]
        results.append({
            "task_id": task["task_id"],
            "original_verse": task["original_verse"],
            "source_verse_sense": "The whole original sentence has a specific meaning.",
            "french_verse_sense": "La phrase française exprime un sens dans son contexte.",
            "clauses": [{
                "original_macula_ids": src,
                "french_spans": [{"word_ids": words}],
                "clause_sense": "The complete clause is interpreted before aligning tokens.",
                "alignments": [
                    {"original_macula_ids": src[:3],
                     "french_spans": [{"word_ids": words[:3]}],
                     "decision": "phrase_span",
                     "contextual_reason": "The source group conveys a complete semantic phrase.",
                     "grammatical_function": None, "uncertainty_reason": None},
                    {"original_macula_ids": src[3:4], "french_spans": [],
                     "decision": "grammatical_unpaired",
                     "contextual_reason": "The original morphological function is conveyed globally.",
                     "grammatical_function": "article", "uncertainty_reason": None},
                    {"original_macula_ids": src[4:],
                     "french_spans": [{"word_ids": words[2:]}],
                     "decision": "phrase_span",
                     "contextual_reason": "One source expression spans several French target words.",
                     "grammatical_function": None, "uncertainty_reason": None},
                ],
            }],
        })
    return {
        "schema_version": 1, "pilot_id": pilot["pilot_id"],
        "review_status": "machine_candidate_only",
        "automatic_approved_links": 0, "publication_authorized": False,
        "results": results,
    }


class WholeVersePilotTests(unittest.TestCase):
    def setUp(self):
        self.dossier = fixture()
        self.pilot, self.report = study.prepare_pilot(
            self.dossier, dossier_sha="f" * 64,
            nt_count=2, ot_count=2)

    def test_balanced_complete_verses_and_source_free_receipt(self):
        self.assertEqual(self.report["verses_by_canon"], {"nt": 2, "ot": 2})
        self.assertEqual(self.report["sampled_unresolved_original_ids"], 40)
        self.assertEqual(self.report["full_verse_original_tokens"], 40)
        self.assertEqual(self.report["model_proposals"], 0)
        self.assertNotIn("La phrase", json.dumps(self.report))
        self.assertFalse(self.pilot["human_gold_supplied_to_model"])
        self.assertEqual(self.pilot["selection_partition"], "training")
        self.assertEqual({t["canon"] for t in self.pilot["tasks"]}, {"ot", "nt"})
        self.assertTrue(all(len(t["original_tokens_in_source_order"]) == 10
                            for t in self.pilot["tasks"]))

    def test_deterministic_private_gzip_identity(self):
        a, _ = study.prepare_pilot(self.dossier, dossier_sha="f" * 64,
                                   nt_count=2, ot_count=2)
        self.assertEqual(study.pack_private(a), study.pack_private(self.pilot))
        self.assertEqual(a["pilot_id"], self.pilot["pilot_id"])

    def test_never_uses_blind_validation_or_calibration(self):
        d = copy.deepcopy(self.dossier)
        candidate = self.pilot["tasks"][0]["original_verse"]
        for case in d["cases"]:
            if case["source_verse_coordinate"] == candidate:
                case["evaluation_partition"] = "blind_validation"
        new, _ = study.prepare_pilot(d, dossier_sha="f" * 64,
                                      nt_count=2, ot_count=2)
        self.assertNotIn(candidate, {t["original_verse"] for t in new["tasks"]})

    def test_excludes_disputed_versification_without_inventing_target(self):
        d = copy.deepcopy(self.dossier)
        verse = self.pilot["tasks"][0]["original_verse"]
        for case in d["cases"]:
            if case["source_verse_coordinate"] == verse:
                case["original_target_verse_disagreement"] = True
        new, _ = study.prepare_pilot(d, dossier_sha="f" * 64,
                                      nt_count=2, ot_count=2)
        self.assertNotIn(verse, {t["original_verse"] for t in new["tasks"]})

    def test_complete_verse_then_phrase_and_grammar_valid(self):
        proposal = valid_response(self.pilot)
        report = study.validate_proposals(self.pilot, proposal)
        self.assertEqual(report["analyzed_complete_verses"], 4)
        self.assertEqual(report["original_source_parts_with_machine_disposition"], 40)
        self.assertEqual(report["machine_dispositions_by_original_part"],
                         {"phrase_span": 36, "grammatical_unpaired": 4})
        self.assertEqual(report["independently_verified_semantic_links"], 0)
        self.assertFalse(report["publication_authorized"])
        self.assertNotIn("form-1", json.dumps(report))

    def test_cross_verse_target_fails(self):
        resp = valid_response(self.pilot)
        resp["results"][0]["clauses"][0]["alignments"][0][
            "french_spans"][0]["word_ids"] = ["01001001:1"]
        with self.assertRaisesRegex(ValueError, "cross-verse|unattested"):
            study.validate_proposals(self.pilot, resp)

    def test_missing_original_token_is_invalid_even_with_good_words(self):
        resp = valid_response(self.pilot)
        resp["results"][0]["clauses"][0]["alignments"][-1][
            "original_macula_ids"].pop()
        with self.assertRaisesRegex(ValueError, "cover every"):
            study.validate_proposals(self.pilot, resp)

    def test_overlap_in_source_must_be_explicit_many_to_many_group(self):
        resp = valid_response(self.pilot)
        first = resp["results"][0]["clauses"][0]["alignments"][0]
        second = resp["results"][0]["clauses"][0]["alignments"][1]
        second["original_macula_ids"] = first["original_macula_ids"][-1:]
        with self.assertRaisesRegex(ValueError, "cover every"):
            study.validate_proposals(self.pilot, resp)

    def test_unpaired_grammar_cannot_force_a_french_word(self):
        resp = valid_response(self.pilot)
        clause = resp["results"][0]["clauses"][0]
        clause["alignments"][1]["french_spans"] = [{
            "word_ids": [clause["french_spans"][0]["word_ids"][0]]}]
        with self.assertRaisesRegex(ValueError, "forced onto French"):
            study.validate_proposals(self.pilot, resp)

    def test_claiming_approval_is_rejected(self):
        resp = valid_response(self.pilot)
        resp["automatic_approved_links"] = 1
        with self.assertRaisesRegex(ValueError, "claims approval"):
            study.validate_proposals(self.pilot, resp)
        resp = valid_response(self.pilot)
        resp["results"][0]["clauses"][0]["alignments"][0]["approved"] = True
        with self.assertRaisesRegex(ValueError, "unsafe fields"):
            study.validate_proposals(self.pilot, resp)

    def test_undetermined_requires_reason_and_no_span(self):
        resp = valid_response(self.pilot)
        row = resp["results"][0]["clauses"][0]["alignments"][0]
        row["decision"] = "undetermined"
        row["french_spans"] = []
        row["uncertainty_reason"] = "unclear_syntax"
        report = study.validate_proposals(self.pilot, resp)
        self.assertEqual(report["machine_dispositions_by_original_part"]["undetermined"], 3)
        row["french_spans"] = [{"word_ids": [self.pilot["tasks"][0][
            "authored_french"]["exact_words"][0]["word_id"]]}]
        with self.assertRaisesRegex(ValueError, "cannot claim"):
            study.validate_proposals(self.pilot, resp)

    def test_duplicate_or_unknown_task_refused(self):
        resp = valid_response(self.pilot)
        resp["results"][1]["task_id"] = resp["results"][0]["task_id"]
        with self.assertRaisesRegex(ValueError, "duplicated"):
            study.validate_proposals(self.pilot, resp)

    def test_source_only_clause_span_must_be_contiguous(self):
        resp = valid_response(self.pilot)
        src = resp["results"][0]["clauses"][0]["original_macula_ids"]
        src[0], src[1] = src[1], src[0]
        with self.assertRaisesRegex(ValueError, "contiguous"):
            study.validate_proposals(self.pilot, resp)

    def test_new_source_disposition_not_auto_linguistic_approval(self):
        resp = valid_response(self.pilot)
        rep = study.validate_proposals(self.pilot, resp)
        self.assertEqual(rep["human_gold_cases_reviewed"], 0)
        self.assertEqual(rep["automatic_approved_links"], 0)
        self.assertFalse(rep["publication_authorized"])


if __name__ == "__main__":
    unittest.main()
