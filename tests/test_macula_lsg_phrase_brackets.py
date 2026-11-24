"""Phrase-boundary negative controls: source ID provenance and no overclaim."""
from __future__ import annotations

import copy
import gzip
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_phrase_brackets", ROOT / "scripts" /
    "audit_macula_lsg_phrase_brackets.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def source(ordinal, canon="n", verse="40001001"):
    return f"{canon}{verse}{ordinal:03d}"


def fixture(words, *, canon="nt", verse="40001001"):
    """Produce faithful tiny grouped rows with direct NT or Aquifer OT anchors."""
    original = [source(i, "n" if canon == "nt" else "o", verse)
                for i in range(1, len(words) + 1)]
    rows = []
    index = {"rows": rows, "by_original_macula_id": {},
             "unlinked_cause_by_original_macula_id": {}}
    for i, (name, target) in enumerate(zip(original, words)):
        if target is None:
            status = "unresolved_no_source_word_witness"
            index["unlinked_cause_by_original_macula_id"][name] = (
                "not_present_in_aquifer_source_alignment_records")
        else:
            status = ("clear_bible_direct_word_only" if canon == "nt"
                      else "aquifer_source_word_witness")
        index["by_original_macula_id"][name] = [len(rows)]
        rows.append({"status": status, "canon": canon,
                     "original_macula_ids": [name],
                     "word_ids": [f"{verse}:{target}"] if target else []})
    return index, original


class BracketTests(unittest.TestCase):
    def test_unlinked_single_between_two_independent_direct_anchors(self):
        index, ids = fixture([1, None, 3])
        before = copy.deepcopy(index)
        found = tool.bounded_groups_for_verse(index, ids, 5)
        self.assertEqual(len(found), 1)
        candidate = found[0]
        self.assertEqual(candidate["original_macula_ids"], [ids[1]])
        self.assertEqual(candidate["lsg_word_ids"], ["40001001:2"])
        self.assertEqual(candidate["anchor_tier"], "clear_bible_direct_nt_word")
        self.assertFalse(candidate["semantic_equivalence_approved"])
        self.assertFalse(candidate["source_words_individually_linked"])
        self.assertTrue(candidate["unpaired_grammar_not_disproved"])
        self.assertEqual(index, before)

    def test_group_to_phrase_is_not_decomposed_into_word_links(self):
        index, ids = fixture([1, None, None, 5])
        candidate, = tool.bounded_groups_for_verse(index, ids, 6)
        self.assertEqual(candidate["original_macula_ids"], ids[1:3])
        self.assertEqual(candidate["lsg_word_ids"], [
            "40001001:2", "40001001:3", "40001001:4"])
        self.assertEqual(candidate["evidence_kind"],
                         "ordered_neighbor_phrase_bracket_only")
        self.assertFalse(candidate["semantic_equivalence_approved"])
        self.assertEqual(tool.bounded_groups_for_verse(
            index, ids, 6, max_original_group=1), [])
        self.assertEqual(tool.bounded_groups_for_verse(
            index, ids, 6, max_french_span=2), [])

    def test_direct_nt_word_mask_removes_gold_and_shared_target(self):
        index, ids = fixture([1, 2, 3])
        self.assertEqual(tool.bounded_groups_for_verse(index, ids, 3), [])
        found = tool.bounded_groups_for_verse(
            index, ids, 3, hidden_source=ids[1],
            hidden_french_word="40001001:2")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["original_macula_ids"], [ids[1]])
        self.assertEqual(found[0]["lsg_word_ids"], ["40001001:2"])
        duplicated_index, duplicated_ids = fixture([1, 2, 2, 3])
        # The neighboring source shares the masked word, but is already
        # linked. It must NOT silently masquerade as an unlinked phrase unit.
        self.assertEqual(tool.bounded_groups_for_verse(
            duplicated_index, duplicated_ids, 3,
            hidden_source=duplicated_ids[1],
            hidden_french_word="40001001:2"), [])

    def test_weak_ot_aquifer_anchor_is_never_promoted_to_gold(self):
        index, ids = fixture([1, None, 3], canon="ot", verse="01001001")
        result, = tool.bounded_groups_for_verse(index, ids, 3)
        self.assertEqual(result["anchor_tier"],
                         "aquifer_surface_attested_ot_candidate")
        self.assertFalse(result["semantic_equivalence_approved"])
        self.assertFalse(result["publication_authorized"])

    def test_crossing_reverse_duplicate_and_outside_anchor_abstain(self):
        reversed_index, ids = fixture([4, None, 2])
        self.assertEqual(tool.bounded_groups_for_verse(reversed_index, ids, 5), [])
        duplicates, ids = fixture([1, None, 1])
        self.assertEqual(tool.bounded_groups_for_verse(duplicates, ids, 5), [])
        crossing, ids = fixture([1, None, 5, 3])
        self.assertEqual(tool.bounded_groups_for_verse(crossing, ids, 6), [])

    def test_existing_non_direct_word_link_cannot_be_replaced(self):
        index, ids = fixture([1, None, 3])
        index["unlinked_cause_by_original_macula_id"].pop(ids[1])
        index["rows"][1]["word_ids"] = ["40001001:2"]
        index["rows"][1]["status"] = "aquifer_source_word_witness"
        self.assertEqual(tool.bounded_groups_for_verse(index, ids, 3), [])

    def test_outside_authored_word_bound_and_reference_fails(self):
        index, ids = fixture([1, None, 5])
        with self.assertRaisesRegex(ValueError, "beyond exact"):
            tool.bounded_groups_for_verse(index, ids, 4)
        second = "n40001002001"
        index["by_original_macula_id"][second] = [len(index["rows"])]
        index["rows"].append({
            "status": "clear_bible_direct_word_only", "canon": "nt",
            "word_ids": ["40001002:1"], "original_macula_ids": [second]})
        with self.assertRaisesRegex(ValueError, "cross-verse"):
            tool.bounded_groups_for_verse(index, ids + [second], 5)
        with self.assertRaisesRegex(ValueError, "unsorted"):
            tool.bounded_groups_for_verse(index, [ids[1], ids[0], ids[2]], 5)

    def test_empty_and_cross_book_candidate_abstentions(self):
        index, ids = fixture([1, None, 2])
        self.assertEqual(tool.bounded_groups_for_verse(index, ids, 5), [])
        self.assertEqual(tool.bounded_groups_for_verse(index, [], 5), [])
        self.assertEqual(tool.bounded_groups_for_verse(index, ids, 0), [])

    def test_masked_holdout_reports_wrong_and_wide_phrase_separately(self):
        gold = {source(2): "40001001:2", source(5): "40001001:9",
                source(8): "40001001:4"}
        predictions = {
            source(2): {"lsg_word_ids": ["40001001:2"]},
            source(5): {"lsg_word_ids": ["40001001:3", "40001001:4"]},
        }
        result = tool.metrics(gold, predictions)
        self.assertEqual(result["cases"], 3)
        self.assertEqual(result["proposed_original_ids"], 2)
        self.assertEqual(result["abstained_original_ids"], 1)
        self.assertEqual(result["target_word_outside_proposed_bracket"], 1)
        self.assertEqual(result["target_word_inside_proposed_bracket"], 1)
        self.assertEqual(result["exact_single_word_target"], 1)
        self.assertEqual(result["bracket_containment_precision"], .5)
        self.assertEqual(result["bracket_width_distribution"], {1:1, 2:1})

    def test_deterministic_private_gzip_no_automatic_approval(self):
        doc = {"brackets": [{"original_macula_ids": [source(2)],
                             "lsg_word_ids": ["40001001:2"],
                             "semantic_equivalence_approved": False}],
               "publication_authorized": False}
        a = tool.compressed_private(doc)
        b = tool.compressed_private(doc)
        self.assertEqual(a, b)
        self.assertEqual(json.loads(gzip.decompress(a)), doc)
        self.assertNotIn(b"Dieu", a)


if __name__ == "__main__":
    unittest.main()
