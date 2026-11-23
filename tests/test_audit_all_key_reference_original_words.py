"""Exhaustive key-reference diagnostics do not promote unreviewed source words."""
from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "key_source_audit", ROOT / "scripts" / "audit_all_key_reference_original_words.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class KeyReferenceCandidateTests(unittest.TestCase):
    def test_separate_direct_and_indirect_and_missing_source_candidate(self):
        with tempfile.TemporaryDirectory() as dirname:
            data = Path(dirname)
            directory = data / "entities" / "people"
            directory.mkdir(parents=True)
            cases = [
                ("Direct", {"explicit_instances":{"wlc":[["o010010010011"]]}}, "already_direct_source_word_check_integrity"),
                ("Indirect", {"pronominal_referents":{"wlc":[["o010010010011"]]}}, "indirect_source_word_not_direct_name"),
                ("Recoverable", {}, "unlinked_original_word_name_candidate_review"),
                ("Unrelated", {}, "key_context_or_unresolved_manual_source_review"),
            ]
            for name, fields, _ in cases:
                (directory / (name + ".json")).write_text(json.dumps({
                    "bsi":{"source_id":"person:"+name},"type":"person",
                    "key_references":["01001001"],"references":[],
                    "localizations":{"eng":{"preferred_label":name}},
                    **fields,
                }),encoding="utf-8")
            rows = mod.inventory(data)
            self.assertEqual(len(rows), 4)
            evidence = {"01001001": [
                {"word_id":"o010010010011","corpus":"wlc","english":"Recoverable",
                 "gloss":"Recoverable","lemma":"x","text":"x"},
            ]}
            result = mod.review(rows,evidence)
            self.assertEqual(len(result["cases"]),4)
            by_id={x["source_id"]:x for x in result["cases"]}
            for name,_,expected in cases:
                self.assertEqual(by_id["person:"+name]["status"],expected)
            self.assertEqual(by_id["person:Recoverable"]["source_word_candidates"]
                             [0]["word_id"],"o010010010011")

    def test_indirect_source_word_is_not_approved_explicit(self):
        row={"source_id":"person:Test","path":"entities/people/Test.json",
             "kind":"person","verse_id":"01001001","names":["test"],
             "source_direct_word_claim":False,"source_indirect_word_claim":True}
        result=mod.review([row],{"01001001":[{
            "word_id":"o010010010011","corpus":"wlc","english":"Test",
            "gloss":"Test","lemma":"x","text":"x"}]})
        self.assertEqual(result["counts"],{"indirect_source_word_not_direct_name":1})
        self.assertEqual(result["cases"][0]["source_word_candidates"][0]
                         ["match_type"],"whole_name_candidate")

    def test_exhaustive_candidate_report_preserves_all_original_words(self):
        row = {"source_id": "place:Complete", "path": "entities/places/Complete.json",
               "kind": "place", "verse_id": "01001001", "names": ["complete"],
               "source_direct_word_claim": False, "source_indirect_word_claim": False}
        words = {"01001001": [
            {"word_id": f"o01001001{i:04d}", "corpus": "wlc",
             "english": "Complete", "gloss": "Complete",
             "lemma": "x", "text": "x"} for i in range(25)
        ]}
        result = mod.review([row], words)
        candidates = result["cases"][0]["source_word_candidates"]
        self.assertEqual(len(candidates), 25)
        self.assertEqual(candidates[-1]["word_id"], "o010010010024")

    def test_real_corpus_covers_every_key_outside_general_without_guessing(self):
        rows=mod.inventory(ROOT/"data")
        self.assertGreater(len(rows),400)
        self.assertEqual(len(rows),len({(x["source_id"],x["verse_id"]) for x in rows}))
        self.assertTrue(all(x["source_id"] and x["path"] for x in rows))
        # Native-structure builds separately verify valid source editions
        # and allow independent key/reference lists; never rewrite either.
if __name__ == "__main__":
    unittest.main()
