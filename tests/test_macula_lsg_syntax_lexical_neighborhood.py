"""Masked original syntax↔authored French neighborhood safety regressions."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


study = module("scripts/audit_macula_lsg_syntax_lexical_neighborhood.py",
               "brsi_syntax_lexical_neighborhood")
fixtures = module("tests/test_macula_lsg_original_syntax.py",
                  "brsi_original_syntax_neighbors_fixture")


def test_data():
    index=fixtures.source_index()
    authored={
        "01001001":"Au commencement Dieu créa",
        "63001001":"L ancien aime les élus",
    }
    parsed=[
        study.syntax.parse_original_syntax(
            fixtures.OT_XML.encode(),"ot",fixtures.OT_PATH),
        study.syntax.parse_original_syntax(
            fixtures.NT_XML.encode(),"nt",fixtures.NT_PATH),
    ]
    return index,authored,parsed


def guess(source,word_id,support=16,share=.8):
    return {
        "source_id":source,"word_id":word_id,
        "support_independent_source_verses":support,
        "share":share,"margin":.75,
        "candidate_only":True,"automatic_linguistic_approval":False,
    }


class SourcePhraseFrenchNeighborhoodTests(unittest.TestCase):
    def test_original_syntax_nested_family_preserves_word_order_and_source(self):
        index,authored,parsed=test_data()
        families,docs=study.syntax_families(parsed)
        self.assertEqual(len(docs),2)
        word=fixtures.OT_IDS[0]
        self.assertEqual(len(families[word]),2)
        self.assertEqual(families[word][0]["original_group_class"],"pp")
        self.assertEqual(families[word][0]["original_macula_ids"],
                         list(fixtures.OT_IDS[:2]))
        self.assertEqual(families[word][1]["original_group_class"],"cl")
        self.assertEqual(families[word][0]["source_verse"],"01001001")
        self.assertEqual(docs["01001001"]["canon"],"ot")
        self.assertEqual(docs["63001001"]["canon"],"nt")

    def test_hebrew_morpheme_word_group_yields_candidate_span_not_approved_link(self):
        index,authored,parsed=test_data()
        families,_=study.syntax_families(parsed)
        source=fixtures.OT_IDS[0]
        before=copy.deepcopy((index,authored,parsed))
        candidate=study.candidate(
            index,authored,source,families[source],
            guess(source,"01001001:2"),radius=2)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["original_macula_phrase_ids"],
                         list(fixtures.OT_IDS[:2]))
        self.assertEqual(candidate["candidate_authored_french_phrase_word_ids"],
                         ["01001001:1","01001001:2"])
        self.assertEqual(candidate["original_syntax_class"],"pp")
        self.assertEqual(candidate["lexical_source_lemma_candidate_french_word_id"],
                         "01001001:2")
        self.assertFalse(candidate[
            "original_source_verse_excluded_from_lexical_training"])
        self.assertTrue(candidate[
            "training_may_include_other_anchors_of_this_unresolved_verse"])
        self.assertTrue(candidate["french_span_is_not_verified_translation"])
        self.assertEqual(candidate["automatic_word_or_phrase_links_approved"],0)
        self.assertFalse(candidate["publication_authorized"])
        self.assertEqual((index,authored,parsed),before)

    def test_french_reordering_expands_either_side_of_existing_anchors(self):
        index,authored,parsed=test_data()
        families,_=study.syntax_families(parsed)
        source=fixtures.OT_IDS[-1]
        candidate=study.candidate(
            index,authored,source,families[source],
            guess(source,"01001001:4"),radius=2)
        self.assertEqual(candidate["candidate_authored_french_phrase_word_ids"],
                         [f"01001001:{i}" for i in (1,2,3,4)])
        self.assertEqual(
            [x["lsg_word_id"] for x in candidate["existing_source_french_anchors"]],
            ["01001001:1","01001001:3"])

    def test_learned_word_far_from_source_syntax_abstains(self):
        index,authored,parsed=test_data()
        families,_=study.syntax_families(parsed)
        source=fixtures.OT_IDS[0]
        far=guess(source,"01001001:4")
        self.assertIsNone(study.candidate(
            index,authored,source,families[source],far,radius=0))
        self.assertIsNotNone(study.candidate(
            index,authored,source,families[source],far,radius=3))
        self.assertIsNone(study.candidate(
            index,authored,source,[],far,radius=4))
        self.assertIsNone(study.candidate(
            index,authored,source,families[source],None,radius=4))

    def test_gold_original_ID_and_all_same_exact_french_word_anchors_masked(self):
        index,authored,parsed=test_data()
        families,_=study.syntax_families(parsed)
        source=fixtures.NT_IDS[2]
        answer="63001001:3"
        candidate=study.candidate(
            index,authored,source,families[source],
            guess(source,answer),hidden_source=source,
            hidden_word=answer,radius=2)
        self.assertEqual(
            [a["lsg_word_id"] for a in candidate["existing_source_french_anchors"]],
            ["63001001:2"])
        self.assertEqual(candidate["candidate_authored_french_phrase_word_ids"],
                         ["63001001:2","63001001:3"])
        self.assertTrue(candidate[
            "original_source_verse_excluded_from_lexical_training"])
        self.assertFalse(candidate[
            "training_may_include_other_anchors_of_this_unresolved_verse"])
        # Even a *different* original source sharing gold target is masked.
        mutated=copy.deepcopy(index)
        other=fixtures.NT_IDS[1]
        row=mutated["by_original_macula_id"][other][0]
        mutated["rows"][row]["word_ids"]=[answer]
        self.assertIsNone(study.candidate(
            mutated,authored,source,families[source],
            guess(source,answer),hidden_source=source,
            hidden_word=answer,radius=2))
        self.assertEqual(
            [a["lsg_word_id"] for a in
             study.original_group_anchors(
                 mutated,families[source][0]["original_macula_ids"],
                 5,hidden_source=source,hidden_word=answer)],[])

    def test_cross_verse_word_ids_and_invalid_text_position_fail_closed(self):
        index,authored,parsed=test_data()
        families,_=study.syntax_families(parsed)
        source=fixtures.OT_IDS[0]
        with self.assertRaisesRegex(ValueError,"another French verse"):
            study.candidate(index,authored,source,families[source],
                            guess(source,"01001002:2"))
        with self.assertRaisesRegex(ValueError,"beyond exact"):
            study.candidate(index,authored,source,families[source],
                            guess(source,"01001001:50"))
        with self.assertRaisesRegex(ValueError,"source not present"):
            study.candidate(index,authored,source,families[fixtures.NT_IDS[0]],
                            guess(source,"01001001:2"))
        with self.assertRaisesRegex(ValueError,"invalid authored"):
            study.candidate(index,authored,source,families[source],
                            guess(source,"01001001:0"))

    def test_wrong_lemma_target_versus_phrase_containment_are_distinct(self):
        source=fixtures.NT_IDS[2]
        gold={source:"63001001:3"}
        lex=guess(source,"63001001:2")
        source_group={
            "original_macula_phrase_ids":list(fixtures.NT_IDS),
            "existing_source_french_anchors":[
                {"original_macula_id":fixtures.NT_IDS[1],
                 "lsg_word_id":"63001001:4"}],
            "candidate_authored_french_phrase_word_ids":[
                "63001001:2","63001001:3","63001001:4"],
        }
        result=study.one_metric(
            gold,{source:(lex,source_group)},{},radius=4,
            threshold=(3,.5))
        self.assertEqual(result["attempted"],1)
        self.assertEqual(result["word_exact_wrong"],1)
        self.assertEqual(result["candidate_phrase_contains_pseudo_gold_word"],1)
        self.assertEqual(result["exact_word_precision"],0)
        self.assertEqual(result[
            "phrase_containment_rate_not_semantic_phrase_accuracy"],1.0)
        self.assertEqual(result["mean_candidate_french_phrase_word_count"],3)

    def test_sample_selection_requires_distinct_real_nt_verses(self):
        index,authored,parsed=test_data()
        docs=study.syntax_families(parsed)[1]
        pivot={"nt":{s:("lemma","noun") for s in fixtures.NT_IDS}}
        with self.assertRaisesRegex(ValueError,"insufficient independent"):
            study.select_nt_pseudo_gold(index,pivot,authored,docs,n=2)
        with self.assertRaisesRegex(ValueError,"insufficient independent"):
            study.select_nt_pseudo_gold(index,pivot,authored,docs,n=1)

    def test_unlinked_source_review_hypotheses_count_semantics_and_abstentions(self):
        index,authored,parsed=test_data()
        families,docs=study.syntax_families(parsed)
        pivots={
            "ot":{fixtures.OT_IDS[0]:("origin-prep","preposition"),
                  fixtures.OT_IDS[3]:("origin-noun","noun")},
            "nt":{fixtures.NT_IDS[0]:("greek-article","article")},
        }
        buckets={
            "lemma":{
                ("ot","origin-prep"):{"commencement":12},
                ("ot","origin-noun"):{"cr\u00e9a":15},
                ("nt","greek-article"):{"L":20},
            },
            "lemma_pos":{},
        }
        private,report=study.unresolved_review_hypotheses(
            index,pivots,authored,families,docs,buckets,radius=4,
            threshold=(3,.5))
        self.assertEqual(sum(
            row.get("total_pinned_original_unlinked_in_scope",0)
            for rows in report.values() for row in rows.values()),3)
        self.assertTrue(all(item["automatic_word_or_phrase_links_approved"]==0
                            for item in private))
        self.assertTrue(all(item["unlinked_reason"] in study.sampler.STRATA
                            for item in private))
        self.assertTrue(all(item["authored_lsg_verse"] in authored.values()
                            for item in private))
        self.assertTrue(all(item["source_original_text"]
                            for item in private))
        self.assertTrue(all(item["publication_authorized"] is False
                            for item in private))


if __name__=="__main__":
    unittest.main()
