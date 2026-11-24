"""Mixed-genre source syntax must not silently create French translations."""
from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load("scripts/audit_macula_lsg_diverse_syntax.py",
           "brsi_diverse_syntax_source_test")
fixtures = load("tests/test_macula_lsg_original_syntax.py",
                "brsi_syntax_frozen_fixture")


def original_annotated_sample():
    parsed = [
        mod.syntax.parse_original_syntax(
            fixtures.OT_XML.encode(), "ot", fixtures.OT_PATH),
        mod.syntax.parse_original_syntax(
            fixtures.NT_XML.encode(), "nt", fixtures.NT_PATH),
    ]
    index = fixtures.source_index()
    authored = {"01001001": "Au commencement Dieu créa",
                "63001001": "L'ancien aime les élus"}
    return index, authored, parsed


class DiverseOriginalReviewUnitTests(unittest.TestCase):
    def test_source_design_has_different_books_genres_and_both_testaments(self):
        self.assertEqual(len(mod.BREADTH_SOURCES), 18)
        self.assertEqual(len({(canon, name) for canon,name,_ in
                              mod.BREADTH_SOURCES}), 18)
        self.assertEqual(sum(x[0] == "ot" for x in mod.BREADTH_SOURCES), 13)
        self.assertEqual(sum(x[0] == "nt" for x in mod.BREADTH_SOURCES), 5)
        self.assertGreater(len({x[2] for x in mod.BREADTH_SOURCES}), 6)
        self.assertTrue(any("Psa-023" in x[1] for x in mod.BREADTH_SOURCES))
        self.assertTrue(any("02-mark" in x[1] for x in mod.BREADTH_SOURCES))
        self.assertTrue(any("27-revelation" in x[1] for x in mod.BREADTH_SOURCES))
        self.assertEqual(mod.BREADTH_FILES,
                         tuple((canon,name) for canon,name,_ in mod.BREADTH_SOURCES))

    def test_private_reviewer_units_deduplicate_constituents_with_shared_unlinked(self):
        index, authored, parsed = original_annotated_sample()
        private, _ = mod.syntax.synthesize(
            index, authored, parsed,
            expected_pilot_files=(( "ot", fixtures.OT_PATH ),
                                  ( "nt", fixtures.NT_PATH )))
        original_private = copy.deepcopy(private)
        clusters, stats = mod.review_units(private["cases"])
        self.assertEqual(private, original_private)
        self.assertEqual(stats["original_ids_represented_in_review_units"],
                         3)
        self.assertEqual(stats["unlinked_original_ids_without_bounded_syntax_unit"],
                         0)
        self.assertEqual(len(clusters), 3)
        self.assertEqual(stats["original_constituent_review_units"], 3)
        self.assertTrue(all(unit["source_syntax_unit_only"] and
                            unit["whole_original_phrase_translated_to_french_not_proven"]
                            and unit["new_source_french_links_approved"] == 0
                            and unit["publication_authorized"] is False
                            for unit in clusters))
        self.assertEqual(len({unit["review_group_id"] for unit in clusters}),
                         len(clusters))

    def test_same_constituent_multiple_unlinked_cases_become_one_dossier(self):
        source = "o010010010011"
        unit = {
            "source_verse": "01001001", "group_id": "literal:wg:1",
            "original_macula_ids": [
                "o010010010011", "o010010010012", "o010010010021"],
            "original_group_class": "pp", "original_group_rule": "PrepNp",
            "original_group_role": "o", "original_source_syntax_depth": 3,
        }
        cue = {
            "french_anchor_word_ids": ["01001001:1", "01001001:3"],
            "french_cue_word_ids": ["01001001:1", "01001001:2",
                                     "01001001:3"],
            "unreviewed_reordering_witness": False,
            "multiple_original_ids_share_french_anchor": True,
        }
        cases = []
        for i, cause in enumerate(mod.sampler.STRATA[:2]):
            cases.append({
                "original_macula_id": unit["original_macula_ids"][i],
                "original_verse": "01001001",
                "source_unlinked_cause": cause,
                "minimum_source_syntactic_constituent": unit,
                "existing_french_anchor_review_cue": cue,
            })
        grouped, report = mod.review_units(cases)
        self.assertEqual(len(grouped), 1)
        self.assertEqual(report["original_ids_represented_in_review_units"], 2)
        self.assertEqual(report["shared_existing_french_anchor_review_units"], 1)
        self.assertEqual(report[
            "source_review_units_with_bounded_french_navigation_cue"], 1)
        self.assertEqual(grouped[0]["unlinked_source_cause_counts"],
                         {cause:1 for cause in mod.sampler.STRATA[:2]})
        self.assertEqual(grouped[0]["original_syntax_role"], "o")
        self.assertEqual(grouped[0]["authored_french_review_cue_word_ids"],
                         cue["french_cue_word_ids"])
        self.assertTrue(grouped[0]["whole_original_phrase_translated_to_french_not_proven"])

    def test_cross_verse_or_inconsistent_authored_anchor_abstains(self):
        unit = {
            "source_verse": "01001001", "group_id": "a:wg:1",
            "original_macula_ids": ["o010010010011", "o010010010012"],
            "original_group_class": "pp",
            "original_group_rule": "PrepNp", "original_group_role": "o",
            "original_source_syntax_depth": 3,
        }
        case = {
            "original_macula_id": "o010010010011",
            "original_verse": "01001001",
            "source_unlinked_cause": mod.sampler.STRATA[1],
            "minimum_source_syntactic_constituent": unit,
            "existing_french_anchor_review_cue": {
                "french_anchor_word_ids": ["01001001:1", "01001001:2"],
                "french_cue_word_ids": ["01001002:1"],
                "unreviewed_reordering_witness": False,
                "multiple_original_ids_share_french_anchor": False,
            },
        }
        with self.assertRaisesRegex(ValueError, "cross-verse"):
            mod.review_units([case])
        case["existing_french_anchor_review_cue"]["french_cue_word_ids"] = [
            "01001001:1"]
        case["original_verse"] = "01001002"
        with self.assertRaisesRegex(ValueError, "incompatible"):
            mod.review_units([case])
        case["original_verse"] = "01001001"
        duplicates = [copy.deepcopy(case), copy.deepcopy(case)]
        with self.assertRaisesRegex(ValueError, "repeated source"):
            mod.review_units(duplicates)

    def test_full_generic_breadth_preserves_original_and_french_text_exactly(self):
        index, authored, parsed = original_annotated_sample()
        before = copy.deepcopy((index, authored, parsed))
        saved = (mod.BREADTH_SOURCES, mod.BREADTH_FILES)
        try:
            mod.BREADTH_SOURCES = (
                ("ot", fixtures.OT_PATH, "law_covenant"),
                ("nt", fixtures.NT_PATH, "letter"),
            )
            mod.BREADTH_FILES = tuple((canon, name) for canon,name,_ in
                                      mod.BREADTH_SOURCES)
            private, report = mod.breadth(index, authored, parsed)
        finally:
            mod.BREADTH_SOURCES, mod.BREADTH_FILES = saved
        self.assertEqual((index, authored, parsed), before)
        self.assertEqual(report["source_verse_count"], 2)
        self.assertEqual(report["source_xml_total_original_token_ids"], 7)
        self.assertEqual(report["unresolved_original_ids_in_selected_source_documents"], 3)
        self.assertEqual(report["source_side_review_units"]["total"], 3)
        self.assertEqual(sum(x["unlinked_indexed_original_ids"] for x in
                             report["per_source_document"]), 3)
        self.assertEqual(report["original_source_XML_ids_already_in_correspondence_index"], 7)
        self.assertEqual(report["correspondence_index_source_ids_not_in_selected_XML"], 1)
        self.assertFalse(report["study_selection_is_random_or_representative"])
        self.assertFalse(report["translation_accuracy_measured"])
        self.assertEqual(report["new_french_word_or_phrase_links_approved"], 0)
        self.assertEqual(report["human_gold_original_to_authored_french_phrase_cases"], 0)
        self.assertFalse(report["publication_authorized"])
        self.assertTrue(private["source_text_preserved_no_translation_equivalence_generated"])
        compressed = mod.phrase.compressed_private(private)
        self.assertEqual(compressed, mod.phrase.compressed_private(private))
        self.assertIn("בְּ", json.dumps(private, ensure_ascii=False))
        self.assertNotIn("בְּ", json.dumps(report, ensure_ascii=False))
        self.assertNotIn("Au commencement", json.dumps(report, ensure_ascii=False))
        self.assertEqual(json.loads(gzip.decompress(compressed)), private)

    def test_source_file_has_unknown_canon_no_fallback_to_other_testament(self):
        index, authored, parsed = original_annotated_sample()
        saved = (mod.BREADTH_SOURCES, mod.BREADTH_FILES)
        try:
            mod.BREADTH_SOURCES = (
                ("ot", fixtures.OT_PATH, "law_covenant"),
                ("nt", fixtures.NT_PATH, "letter"),
            )
            mod.BREADTH_FILES = tuple((canon, name) for canon,name,_ in
                                      mod.BREADTH_SOURCES)
            malformed = copy.deepcopy(parsed)
            malformed[1]["source_file"] = "wrong-original-path"
            with self.assertRaisesRegex(ValueError, "unexpected pinned syntax"):
                mod.breadth(index, authored, malformed)
            self.assertEqual(parsed[1]["source_file"], fixtures.NT_PATH)
        finally:
            mod.BREADTH_SOURCES, mod.BREADTH_FILES = saved


if __name__ == "__main__":
    unittest.main()
