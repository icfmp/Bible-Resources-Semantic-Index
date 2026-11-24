"""Fail-closed lexical↔phrase consensus negative controls and calibration."""
from __future__ import annotations

import copy
import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_consensus", ROOT / "scripts" /
    "audit_macula_lsg_contextual_consensus.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def guess(source="n40001001002", word="40001001:2",
          support=16, share=.85, margin=.75):
    return {
        "source_id": source,
        "word_id": word,
        "word_sha256": "0" * 64,
        "lemma_sha256": "1" * 64,
        "support_independent_source_verses": support,
        "share": share, "margin": margin,
        "candidate_only": True, "automatic_linguistic_approval": False,
    }


def bracket(source="n40001001002", words=None, ids=None):
    return {
        "source_verse": source[1:9],
        "original_macula_ids": [source] if ids is None else ids,
        "lsg_word_ids": ["40001001:2"] if words is None else words,
        "anchor_tier": "clear_bible_direct_nt_word",
        "semantic_equivalence_approved": False,
    }


class ConsensusTests(unittest.TestCase):
    def test_single_word_lexical_agreement_never_production_link(self):
        src = "n40001001002"
        a = guess()
        b = bracket()
        originals = copy.deepcopy((a, b))
        c = tool.consensus(src, a, b)
        self.assertEqual(c["source_id"], src)
        self.assertEqual(c["lsg_phrase_word_ids"], ["40001001:2"])
        self.assertEqual(c["lemma_suggested_lsg_word_id"], "40001001:2")
        self.assertTrue(tool.eligible(c, (12, .8), "single_word_bracket"))
        self.assertFalse(tool.eligible(c, (20, .85), "single_word_bracket"))
        self.assertFalse(c["automatic_linguistic_approval"])
        self.assertFalse(c["publication_authorized"])
        self.assertFalse(c["word_level_semantic_equivalence_proven"])
        self.assertFalse(c["group_phrase_semantic_equivalence_proven"])
        self.assertFalse(c["independently_human_reviewed"])
        self.assertEqual((a, b), originals)

    def test_many_to_many_bracket_is_not_split_into_individual_links(self):
        src = "n40001001002"
        a = guess(word="40001001:3")
        b = bracket(src, words=["40001001:2", "40001001:3",
                                 "40001001:4"],
                    ids=["n40001001002", "n40001001003"])
        result = tool.consensus(src, a, b)
        self.assertEqual(result["source_group_macula_ids"], [
            "n40001001002", "n40001001003"])
        self.assertTrue(tool.eligible(result, (12, .8), "any_bounded_phrase"))
        self.assertFalse(tool.eligible(result, (12, .8),
                                       "single_word_bracket"))
        self.assertFalse(result["source_words_individually_linked"])

    def test_both_missing_and_competing_signals_abstain(self):
        src = "n40001001002"
        self.assertIsNone(tool.consensus(src, None, bracket()))
        self.assertIsNone(tool.consensus(src, guess(), None))
        self.assertIsNone(tool.consensus(src, guess(word="40001001:5"),
                                         bracket()))
        with self.assertRaisesRegex(ValueError, "non-member"):
            tool.consensus(src, guess(), bracket(ids=["n40001001003"]))
        with self.assertRaisesRegex(ValueError, "unknown"):
            tool.eligible({}, (3, .5), "undocumented_threshold")
        source = "n40001002002"
        b = bracket(src)
        b["original_macula_ids"].append(source)
        with self.assertRaisesRegex(ValueError, "cross-verse"):
            tool.consensus(source, guess(source=source), b)

    def test_gold_requires_exact_lemma_word_not_just_phrase_containment(self):
        src1 = "n40001001001"
        src2 = "n40001002001"
        src3 = "n40001003001"
        gold = {src1:"40001001:2",
                src2:"40001002:3",
                src3:"40001003:4"}
        predictions = {
            src1: tool.consensus(
                src1, guess(src1, "40001001:2"),
                bracket(src1, ["40001001:1", "40001001:2"])),
            src2: tool.consensus(
                src2, guess(src2, "40001002:1"),
                {"source_verse":"40001002","original_macula_ids":[src2],
                 "lsg_word_ids":["40001002:1","40001002:2","40001002:3"],
                 "anchor_tier":"clear_bible_direct_nt_word"}),
            src3: None}
        res = tool.error_metrics(gold, predictions, (3,.5),
                                 "any_bounded_phrase")
        self.assertEqual(res["attempted"], 2)
        self.assertEqual(res["word_exact_correct"], 1)
        self.assertEqual(res["word_exact_wrong"], 1)
        self.assertEqual(res["phrase_contains_gold_word"], 2)
        self.assertEqual(res["phrase_contains_gold_but_lemma_word_wrong"], 1)
        self.assertEqual(res["abstained"], 1)
        self.assertEqual(res["exact_word_precision"], .5)
        self.assertFalse(tool.error_metrics(gold, predictions, (20,.9),
                                            "any_bounded_phrase")["attempted"])

    def test_threshold_selection_calibration_only_and_blind_no_leak(self):
        gold = {}
        predictions = {}
        for i in range(40):
            verse = f"40001{i + 1:03d}"
            source = f"n{verse}001"
            target = f"{verse}:2"
            gold[source] = target
            predictions[source] = tool.consensus(
                source, guess(source, target),
                {"source_verse":verse, "original_macula_ids":[source],
                 "lsg_word_ids":[target],
                 "anchor_tier":"clear_bible_direct_nt_word"})
        rule, grid = tool.frozen_threshold(gold, predictions)
        self.assertEqual(rule["mode"], "any_bounded_phrase"
                         if rule["mode"] == "any_bounded_phrase"
                         else "single_word_bracket")
        self.assertEqual(rule["min_source_verses"], 3)
        self.assertEqual(len(grid),
                         len(tool.MODES) * len(tool.THRESHOLDS))
        self.assertTrue(all(r["cases"] == 40 for r in grid))
        self.assertTrue(all(r["not_independent_phrase_semantic_accuracy"]
                            for r in grid))
        # 20/40 correct cannot clear the predeclared precision gate.
        for idx, source in enumerate(gold):
            if idx % 2:
                gold[source] = f"{source[1:9]}:1"
        rejected, _ = tool.frozen_threshold(gold, predictions)
        self.assertIsNone(rejected)

    def test_phrase_conditioning_recovers_repeated_verse_word_only_if_locally_unique(self):
        source = "n40001001002"
        pivot = {source: ("θεός", "n")}
        lexicon = {
            "lemma": {("nt", "θεός"): {"dieu": 15, "seigneur": 8}},
            "lemma_pos": {},
        }
        authored = {"40001001": "Dieu et Seigneur Dieu"}
        words = ["40001001:3", "40001001:4"]
        group = bracket(source, words=words)
        global_guess = tool.lexical.predict(
            source, pivot, authored, {}, lexicon)
        self.assertEqual(global_guess["word_id"], "40001001:3")
        constrained = tool.constrained_lexical_candidate(
            source, pivot, authored, {}, lexicon, group)
        self.assertEqual(constrained["lemma_suggested_lsg_word_id"],
                         "40001001:4")
        self.assertEqual(constrained["lsg_phrase_word_ids"], words)
        self.assertEqual(constrained["support_independent_source_verses"], 15)
        self.assertTrue(constrained["lexical_selection_restricted_to_bounded_phrase"])
        self.assertFalse(constrained["word_level_semantic_equivalence_proven"])
        self.assertFalse(constrained["publication_authorized"])
        self.assertTrue(tool.eligible(constrained, (12, .6),
                                      "any_bounded_phrase"))
        self.assertFalse(tool.eligible(constrained, (20, .6),
                                       "any_bounded_phrase"))

    def test_phrase_conditioning_abstains_on_duplicate_tie_or_no_attested_lemma(self):
        source = "n40001001002"
        pivot = {source: ("θεός", "n")}
        counts = {"lemma": {("nt", "θεός"): {"dieu": 10,
                                            "seigneur": 10}},
                  "lemma_pos": {}}
        authored = {"40001001": "Dieu Seigneur"}
        group = bracket(source, words=["40001001:1", "40001001:2"])
        self.assertIsNone(tool.constrained_lexical_candidate(
            source, pivot, authored, {}, counts, group))
        unique = {"lemma": {("nt", "θεός"): {"dieu": 20}},
                  "lemma_pos": {}}
        repeated = {"40001001": "Dieu Dieu"}
        self.assertIsNone(tool.constrained_lexical_candidate(
            source, pivot, repeated, {}, unique, group))
        self.assertIsNone(tool.constrained_lexical_candidate(
            source, {source: ("nonexistent", "n")}, authored, {},
            unique, group))
        self.assertIsNone(tool.constrained_lexical_candidate(
            source, pivot, authored, {}, unique, None))
        bad = bracket(source, words=["40001002:1"])
        with self.assertRaisesRegex(ValueError, "non-authorial"):
            tool.constrained_lexical_candidate(
                source, pivot, authored, {}, unique, bad)
        bad = bracket(source, words=["40001001:50"])
        with self.assertRaisesRegex(ValueError, "beyond French"):
            tool.constrained_lexical_candidate(
                source, pivot, authored, {}, unique, bad)

    def test_absent_predictions_fail_closed_and_width_never_invents_words(self):
        src = "n40001001002"
        token = tool.consensus(src, guess(), bracket())
        self.assertFalse(tool.eligible(token, (50,.95),
                                       "any_bounded_phrase"))
        self.assertFalse(tool.eligible(None, (3,.5),
                                       "any_bounded_phrase"))
        with self.assertRaisesRegex(ValueError, "case set"):
            tool.error_metrics({src:"40001001:2"}, {}, (3,.5),
                               "any_bounded_phrase")
        invalid = bracket()
        invalid["lsg_word_ids"] = ["40001001:2", "40001002:1"]
        with self.assertRaisesRegex(ValueError, "invalid authored"):
            tool.consensus(src, guess(), invalid)

    def test_masked_direct_nt_bracket_is_available_without_gold_as_anchor(self):
        ids = ["n40001001001", "n40001001002", "n40001001003"]
        rows = []
        index = {"rows": rows, "by_original_macula_id": {},
                 "unlinked_cause_by_original_macula_id": {}}
        for i, source in enumerate(ids):
            index["by_original_macula_id"][source] = [i]
            rows.append({"canon":"nt",
                         "original_macula_ids":[source],
                         "word_ids":[f"40001001:{i+1}"],
                         "status":"clear_bible_direct_word_only"})
        self.assertEqual(tool.phrase.bounded_groups_for_verse(
            index, ids, 3), [])
        bounded = tool.phrase.bounded_groups_for_verse(
            index, ids, 3, hidden_source=ids[1],
            hidden_french_word="40001001:2")
        self.assertEqual(len(bounded), 1)
        self.assertEqual(bounded[0]["lsg_word_ids"], ["40001001:2"])
        self.assertEqual(tool.consensus(ids[1], guess(ids[1]), bounded[0])[
            "lemma_suggested_lsg_word_id"], "40001001:2")


if __name__ == "__main__":
    unittest.main()
