"""Blind lexical-evidence pilot: original MACULA IDs and authored French words."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "contextual_lexical_pilot",
    ROOT / "scripts" / "audit_macula_lsg_contextual_lexical_pilot.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def mini_index():
    source_nt = ["n40001001001", "n40001002001",
                 "n40001003001", "n40001004001"]
    source_ot = ["o01001001001"]
    rows = []
    by_source = {}
    for source in source_nt:
        verse = source[1:9]
        by_source[source] = [len(rows)]
        rows.append({
            "original_macula_ids": [source], "canon": "nt",
            "word_ids": [verse + ":1"],
            "status": "clear_bible_direct_word_only",
        })
    for source in source_ot:
        by_source[source] = [len(rows)]
        rows.append({
            "original_macula_ids": [source], "canon": "ot",
            "word_ids": [source[1:9] + ":1"],
            "status": "aquifer_source_word_witness",
        })
    for source in ("n40001005001", "o01001002001",
                   "o01001003001", "o01001004001"):
        by_source[source] = [len(rows)]
        rows.append({"original_macula_ids": [source], "canon": (
            "nt" if source.startswith("n") else "ot"),
            "word_ids": [], "status": "unresolved_no_source_word_witness"})
    return {
        "rows": rows,
        "by_original_macula_id": by_source,
        "unlinked_cause_by_original_macula_id": {
            "n40001005001": "aquifer_record_source_with_no_uniquely_located_french_word",
            "o01001002001": "aquifer_explicit_non_equivalent_source",
            "o01001003001": "not_present_in_aquifer_source_alignment_records",
            "o01001004001": "other_part_of_same_original_word_has_link",
        },
    }


class PilotTests(unittest.TestCase):
    def test_pivot_source_exact_hash_and_source_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.tsv"
            raw = "xml:id\tlemma\tsp\n40001001001\tθεός\tN\n40001002001\tλόγος\tN\n"
            path.write_text(raw, encoding="utf-8")
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            source, census = pilot.pivot_source(path, "nt", sha)
            self.assertEqual(source["n40001001001"], (pilot.norm("θεός"), "n"))
            self.assertEqual(census["pos_column"], "sp")
            self.assertEqual(census["tokens"], 2)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                pilot.pivot_source(path, "nt", "0"*64)
            path.write_text(raw+"40001001001\tθεός\tN\n", encoding="utf-8")
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "duplicate"):
                pilot.pivot_source(path, "nt", sha)

    def test_exact_authorial_word_and_multigroup_abstention(self):
        index = mini_index()
        self.assertEqual(pilot.one_word_id(index, "n40001001001", direct_only=True),
                         "40001001:1")
        self.assertEqual(pilot.one_word_id(index, "o01001001001", direct_only=True),
                         None)
        self.assertEqual(pilot.one_word_id(index, "o01001001001"), "01001001:1")
        index["rows"].append({
            "canon": "nt", "original_macula_ids": ["n40001001001"],
            "status": "aquifer_source_word_witness",
            "word_ids": ["40001001:2"],
        })
        index["by_original_macula_id"]["n40001001001"].append(
            len(index["rows"])-1)
        self.assertIsNone(pilot.one_word_id(index, "n40001001001"))
        self.assertEqual(pilot.one_word_id(
            index, "n40001001001", direct_only=True), "40001001:1")

    def test_blind_gold_verseevidence_is_excluded_from_training(self):
        index = mini_index()
        sources = {s: ("θεός", "n") for s in index["by_original_macula_id"]
                   if s.startswith("n")}
        text = {s[1:9]: "Dieu nous parle" for s in sources}
        selected = pilot.select_blind_gold(index, sources, text, n=2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(len({s[1:9] for s in selected}), 2)
        all_pivots = {"nt": sources, "ot": {
            s:("אֱלֹהִים", "n") for s in index["by_original_macula_id"]
            if s.startswith("o")}}
        buckets, counts = pilot.lexical_buckets(
            index, all_pivots, {**text, "01001001": "Dieu agit"},
            {s[1:9] for s in selected})
        self.assertEqual(counts["nt_original_training_source_ids"], 2)
        self.assertEqual(sum(buckets["lemma"][("nt","θεός")].values()), 2)

    def test_lemma_context_prediction_requires_unique_surface(self):
        source="n40001005001"
        piv={source: ("θεός", "n")}
        authored = {"40001005": "Dieu aime les hommes"}
        buckets={"lemma":{("nt","θεός"):{"dieu":20,"hommes":1}},
                 "lemma_pos":{("nt","θεός","n"):{"dieu":16,"hommes":1}}}
        result=pilot.predict(source,piv,authored,{},buckets)
        self.assertEqual(result["word_id"],"40001005:1")
        self.assertEqual(result["support_independent_source_verses"],16)
        self.assertTrue(result["pivot_morphology_used"])
        self.assertTrue(pilot.qualifies(result,(12,.8)))
        self.assertFalse(pilot.qualifies(result,(30,.9)))
        self.assertFalse(result["automatic_linguistic_approval"])
        self.assertIsNone(pilot.predict(
            source,piv,{"40001005":"Dieu et Dieu"}, {}, buckets))
        self.assertIsNone(pilot.predict(
            source,{source:("", "n")},authored,{},buckets))

    def test_ambiguous_target_and_disagreed_lexical_senses_abstain(self):
        buckets={"lemma":{("nt","logos"):{"parole":5,"mot":5}},
                 "lemma_pos":{}}
        source="n40001005001"
        self.assertIsNone(pilot.predict(
            source,{source:("logos","")}, {"40001005":"la parole et le mot"},
            {},buckets))
        self.assertIsNone(pilot.predict(
            source,{source:("logos","")}, {"40001005":"la vérité"},
            {},buckets))

    def test_holdout_cannot_be_gamed_by_unresolved_source_ids(self):
        index=mini_index()
        pivots={
            "nt":{s:("θεός","n") for s in index["by_original_macula_id"]
                  if s.startswith("n")},
            "ot":{s:("אֱלֹהִים","n") for s in index["by_original_macula_id"]
                  if s.startswith("o")},
        }
        authored={s[1:9]:"Dieu dit" for s in index["by_original_macula_id"]}
        result, candidates=pilot.pilot(
            index,pivots,authored,validation_words=2,
            preview_per_stratum=1)
        self.assertEqual(result["nt_gold_size"],2)
        self.assertEqual(result["nt_gold_verses_held_out_from_all_lexical_training"],2)
        self.assertEqual(result["unresolved_original_source_count"],4)
        self.assertEqual(len(result["unresolved_original_source_by_cause"]),4)
        self.assertFalse(result["blind_validation_half"]["pilot_precision_gate_passed"])
        self.assertTrue(result["no_new_source_word_link_accepted"])
        self.assertFalse(result["semantic_translation_approved"])
        self.assertTrue(all(p["candidate_only"] for p in candidates))

    def test_wilson_bounds_and_training_thresholds_are_explicit(self):
        gold={"n40001001001":"40001001:1",
              "n40001002001":"40001002:1"}
        predictions={
            "n40001001001":{"word_id":"40001001:1",
                             "support_independent_source_verses":10,
                             "share":.8,"margin":.7},
            "n40001002001":{"word_id":"40001002:2",
                             "support_independent_source_verses":3,
                             "share":.6,"margin":.2},
        }
        self.assertEqual(pilot.metrics(gold,predictions,None)["precision"],.5)
        self.assertEqual(pilot.metrics(gold,predictions,(8,.7))["precision"],1.)
        self.assertEqual(pilot.metrics(gold,predictions,(8,.7))["proposed"],1)
        self.assertLess(pilot.metrics(gold,predictions,(8,.7))[
            "precision_wilson95_lower"],1.)
        self.assertEqual(pilot.metrics(gold,predictions,(30,.9))["proposed"],0)


if __name__ == "__main__":
    unittest.main()
