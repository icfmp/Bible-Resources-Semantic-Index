"""Original MACULA syntax anchor-only brackets: negative and privacy regressions."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


study = module("scripts/audit_macula_lsg_syntax_anchor_only.py",
               "brsi_anchor_only_research")
fixtures = module("tests/test_macula_lsg_original_syntax.py",
                  "brsi_original_macula_anchor_only_fixtures")


def sample():
    index = fixtures.source_index()
    authored = {
        "01001001": "Au commencement Dieu créa",
        "63001001": "L ancien aime les élus",
    }
    parsed = [
        study.syntax.parse_original_syntax(
            fixtures.OT_XML.encode(), "ot", fixtures.OT_PATH),
        study.syntax.parse_original_syntax(
            fixtures.NT_XML.encode(), "nt", fixtures.NT_PATH),
    ]
    groups, _ = study.base.syntax_families(parsed)
    return index, authored, parsed, groups


class AnchorOnlySyntaxReviewTests(unittest.TestCase):
    def test_actual_original_constituent_creates_two_anchor_review_bracket(self):
        index, authored, parsed, groups = sample()
        source = fixtures.OT_IDS[-1]
        prior = copy.deepcopy((index, authored, parsed))
        proposal = study.anchor_bracket(index, authored, source, groups[source])
        self.assertIsNotNone(proposal)
        self.assertEqual(
            proposal["bounded_authored_french_navigation_word_ids"],
            ["01001001:1", "01001001:2", "01001001:3"])
        self.assertEqual(proposal["original_macula_phrase_ids"],
                         list(fixtures.OT_IDS))
        self.assertEqual(proposal["independently_located_distinct_anchor_words"], 2)
        self.assertEqual(proposal["span_width"], 3)
        self.assertFalse(proposal["lexical_translation_guess_required"])
        self.assertTrue(proposal["source_group_is_authentic"])
        self.assertTrue(proposal["French_span_is_only_navigation_not_translation"])
        self.assertFalse(proposal["human_phrase_semantic_gold"])
        self.assertFalse(proposal["publication_authorized"])
        self.assertEqual(proposal["automatic_link_approvals"], 0)
        self.assertEqual(prior, (index, authored, parsed))

    def test_without_two_distinct_target_words_the_small_group_abstains(self):
        index, authored, _, groups = sample()
        original = fixtures.OT_IDS[0]
        self.assertIsNone(study.anchor_bracket(
            index, authored, original, groups[original][:1]))
        self.assertIsNone(study.anchor_bracket(
            index, authored, original, groups[original], max_width=2))
        self.assertIsNone(study.anchor_bracket(
            index, authored, original, [], max_width=16))

    def test_exclude_hidden_gold_and_any_original_anchor_sharing_it(self):
        index, authored, _, groups = sample()
        source = fixtures.OT_IDS[-1]
        self.assertIsNotNone(study.anchor_bracket(
            index, authored, source, groups[source]))
        self.assertIsNone(study.anchor_bracket(
            index, authored, source, groups[source],
            hidden_source=source, hidden_word="01001001:1"))
        self.assertIsNone(study.anchor_bracket(
            index, authored, source, groups[source],
            hidden_source=source, hidden_word="01001001:3"))

    def test_source_group_for_wrong_verse_rejected_not_silently_shifted(self):
        index, authored, _, groups = sample()
        original = fixtures.OT_IDS[-1]
        wrong = copy.deepcopy(groups[original][0])
        wrong["source_verse"] = "01001002"
        with self.assertRaisesRegex(ValueError, "original XML constituent"):
            study.anchor_bracket(index, authored, original, [wrong])

    def test_invalid_or_out_of_bounds_existing_anchor_fails_closed(self):
        index, authored, _, groups = sample()
        original = fixtures.OT_IDS[-1]
        bad = copy.deepcopy(index)
        other = fixtures.OT_IDS[2]
        row = bad["by_original_macula_id"][other][0]
        bad["rows"][row]["word_ids"] = ["01001001:99"]
        with self.assertRaisesRegex(ValueError, "exceeds exact French"):
            study.anchor_bracket(bad, authored, original, groups[original])

    def test_one_target_word_shared_by_multiple_source_ids_is_one_anchor(self):
        index, authored, _, groups = sample()
        original = fixtures.OT_IDS[-1]
        bad = copy.deepcopy(index)
        # All already-linked sources inside this group now point to the
        # *same* existing French word. No invented second target is allowed.
        for source in fixtures.OT_IDS:
            if source not in bad["by_original_macula_id"]:
                continue
            for row in bad["by_original_macula_id"][source]:
                if bad["rows"][row].get("word_ids"):
                    bad["rows"][row]["word_ids"] = ["01001001:1"]
        self.assertIsNone(study.anchor_bracket(
            bad, authored, original, groups[original]))

    def test_metric_containment_is_distinct_from_semantic_equivalence(self):
        original = fixtures.OT_IDS[-1]
        proposal = {
            "bounded_authored_french_navigation_word_ids": [
                "01001001:1", "01001001:2", "01001001:3"],
            "span_width": 3,
            "original_macula_phrase_ids": list(fixtures.OT_IDS),
        }
        expected = {original: "01001001:2"}
        metrics = study.bracket_metric(expected, {original: proposal}, width=3)
        self.assertEqual(metrics["attempted"], 1)
        self.assertEqual(metrics["contained_source_attested_pseudo_gold_word"], 1)
        self.assertEqual(metrics["missed_source_attested_pseudo_gold_word"], 0)
        self.assertEqual(metrics["positional_containment_not_phrase_semantic_precision"], 1)
        self.assertEqual(metrics["average_french_navigation_width"], 3)
        self.assertEqual(study.bracket_metric(
            expected, {original: proposal}, 2)["abstained"], 1)
        self.assertEqual(study.bracket_metric(
            {original: "01001001:4"}, {original: proposal}, 4)[
                "missed_source_attested_pseudo_gold_word"], 1)

    def test_metric_abstains_on_no_bracket_and_rejects_partition_mismatch(self):
        original = fixtures.OT_IDS[0]
        m = study.bracket_metric({original: "01001001:2"}, {original: None}, 16)
        self.assertEqual(m["cases"], 1)
        self.assertEqual(m["attempted"], 0)
        self.assertEqual(m["abstained"], 1)
        self.assertEqual(m["wilson95_lower"], 0)
        with self.assertRaisesRegex(ValueError, "partition mismatch"):
            study.bracket_metric({original: "01001001:2"}, {}, 16)

    def test_no_lexical_guess_needed_and_no_generated_new_authorial_text(self):
        index, authored, _, groups = sample()
        proposal = study.anchor_bracket(
            index, authored, fixtures.OT_IDS[-1], groups[fixtures.OT_IDS[-1]])
        self.assertNotIn("lexical_source_lemma_candidate_french_word_id", proposal)
        self.assertNotIn("authored_french_verse_private", proposal)
        self.assertTrue(all(
            word_id.startswith("01001001:")
            for word_id in proposal["bounded_authored_french_navigation_word_ids"]))


if __name__ == "__main__":
    unittest.main()
