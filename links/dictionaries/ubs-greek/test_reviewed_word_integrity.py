#!/usr/bin/env python3
"""Shared regression tests for exact Greek source-word review transitions."""
from __future__ import annotations

import copy
import runpy
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
GUARD=runpy.run_path(str(HERE/"reviewed_word_integrity.py"))
PENDING="unapproved_original_source_word_only"
REVIEWED="reviewed_source_headword_only"


def fixture():
    word={
        "word_id":"n40001001001", "original_lemma":"λόγος",
        "original_strong":"3056", "original_ln":"33.98",
        "reference":"MAT 1:1!1", "original_class":"noun",
        "original_morph":"N-NSM", "attested_headword_ln_codes":["33.98"],
    }
    record={
        "entry_id":"000010000000000", "match_type":PENDING,
        **{target:word[source] for target,source in GUARD["WITNESS_FIELDS"]},
        "keep_original_provenance":"source-pinned",
    }
    other={"entry_id":"000020000000000","match_type":"already_source_reviewed",
           "original_strong":"1","original_ln":"","sense_ids":[]}
    document={
        "by_macula_word":{word["word_id"]:record,"n40001001002":other},
        "by_strong":{"3056":["000010000000000"]},
        "editorial_candidate":{"publication_approved":False,
                               "new_inferred_contextual_lexical_sense_ids":0},
        "word_aware_coverage":{"source_original_words":137741},
    }
    return document,word


class ExactReviewedWordEvidenceTests(unittest.TestCase):
    def test_source_word_and_metadata_are_preserved_while_status_changes(self):
        original,witness=fixture()
        untouched=copy.deepcopy(original)
        wid=witness["word_id"]
        GUARD["verify_original_word"](
            original["by_macula_word"][wid],witness,wid,
            "000010000000000",PENDING)
        reviewed=GUARD["apply_review_status"](original,{wid},PENDING,REVIEWED)
        self.assertEqual(original,untouched)
        self.assertEqual(reviewed["by_macula_word"][wid]["match_type"],REVIEWED)
        for key,old in original.items():
            if key!="by_macula_word":
                self.assertEqual(reviewed[key],old)
        self.assertEqual(reviewed["by_macula_word"]["n40001001002"],
                         original["by_macula_word"]["n40001001002"])
        for key,value in untouched["by_macula_word"][wid].items():
            if key!="match_type":
                self.assertEqual(reviewed["by_macula_word"][wid][key],value)
        self.assertNotIn("sense_id",reviewed["by_macula_word"][wid])

    def test_every_original_source_annotation_drift_rejected(self):
        original,witness=fixture()
        wid=witness["word_id"]
        actual=original["by_macula_word"][wid]
        for field,wrong in (
            ("original_lemma","λογος"),("original_strong","G3056"),
            ("original_ln","33.99"),("original_reference","MAT 1:2!1"),
            ("original_class","verb"),("original_morph","V-NSM"),
            ("corroborating_ubs_ln_codes",["33.99"]),
            ("entry_id","000020000000000"),("match_type","already_reviewed")
        ):
            altered=copy.deepcopy(actual)
            altered[field]=wrong
            with self.subTest(field=field),self.assertRaisesRegex(
                    ValueError,"word witness drift"):
                GUARD["verify_original_word"](
                    altered,witness,wid,"000010000000000",PENDING)

    def test_reject_missing_or_wrong_word_source_witness(self):
        original,witness=fixture()
        wid=witness["word_id"]
        row=original["by_macula_word"][wid]
        altered=copy.deepcopy(witness)
        altered["word_id"]="n40001001002"
        with self.assertRaisesRegex(ValueError,"word-ID does not match"):
            GUARD["verify_original_word"](row,altered,wid,"000010000000000",PENDING)
        altered=copy.deepcopy(witness)
        del altered["original_morph"]
        with self.assertRaisesRegex(ValueError,"fields missing"):
            GUARD["verify_original_word"](row,altered,wid,"000010000000000",PENDING)
        with self.assertRaisesRegex(ValueError,"witness missing"):
            GUARD["verify_original_word"](None,witness,wid,"000010000000000",PENDING)

    def test_original_strong_zero_is_literal_not_an_alias(self):
        # Strong=0 in the original source must remain exactly "0"; this
        # shared mechanical check never invents a Strong alias.
        original,witness=fixture()
        wid=witness["word_id"]
        witness["original_strong"]="0"
        original["by_macula_word"][wid]["original_strong"]="0"
        guard=GUARD["verify_original_word"]
        guard(original["by_macula_word"][wid],witness,wid,
              "000010000000000",PENDING)
        bad=copy.deepcopy(original["by_macula_word"][wid])
        bad["original_strong"]="3056"
        with self.assertRaisesRegex(ValueError,"original_strong"):
            guard(bad,witness,wid,"000010000000000",PENDING)
        promoted=GUARD["apply_review_status"](original,{wid},PENDING,REVIEWED)
        self.assertEqual(promoted["by_macula_word"][wid]["original_strong"],"0")
        self.assertNotIn("sense_id",promoted["by_macula_word"][wid])

    def test_wrong_existing_status_missing_or_duplicate_word_rejected(self):
        original,witness=fixture()
        wid=witness["word_id"]
        for ids in ([],[wid,wid],["unknown-id"]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):
                GUARD["apply_review_status"](original,ids,PENDING,REVIEWED)
        with self.assertRaisesRegex(ValueError,"already reviewed or not pending"):
            GUARD["apply_review_status"](
                original,["n40001001002"],PENDING,REVIEWED)
        with self.assertRaisesRegex(ValueError,"status transition malformed"):
            GUARD["apply_review_status"](original,[wid],PENDING,PENDING)
        self.assertFalse(original["editorial_candidate"]["publication_approved"])


if __name__=="__main__":
    unittest.main()
