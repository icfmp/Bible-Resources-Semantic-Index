"""Source-word research candidates must be read-only, literal and uncertain."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_place_word_triage",
    ROOT / "scripts" / "audit_place_source_word_candidates.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PlaceWordTriageTests(unittest.TestCase):
    def test_english_gloss_candidate_never_edits_source_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / "entities" / "places" / "Aijalon.2.json"
            p.parent.mkdir(parents=True)
            value = {
                "id": "place:Aijalon.2", "type": "place",
                "mentioned_in_bible": True, "references": [],
                "key_references": ["07012012"], "explicit_instances": {},
                "localizations": {"eng": {"preferred_label": "Aijalon (of Zebulun)"}},
                "bsi": {"source_id": "place:Aijalon.2"},
            }
            p.write_text(json.dumps(value), encoding="utf-8")
            original = p.read_bytes()
            header = "xml:id\tenglish\tgloss\tlemma\ttext\n"
            wlc = root / "hebrew.tsv"
            wlc.write_text(header + "o070120120081\tAijalon\tAijalon\tאילון\tאַיָּלוֹן\n")
            greek = root / "greek.tsv"
            greek.write_text(header + "n40001001001\tJesus\tJesus\tΙησούς\tἸησοῦς\n")
            rows = mod.source_candidate_places(root)
            self.assertEqual(len(rows), 1)
            words = mod.source_word_evidence(rows, {"wlc": wlc, "sblgnt": greek})
            self.assertEqual(list(words), ["07012012"])
            report = mod.triage(rows, words)
            self.assertEqual(report["counts"],
                             {"matching_original_word_candidate_review_required": 1})
            self.assertEqual(report["cases"][0]["matching_source_words"][0]["word_id"],
                             "o070120120081")
            self.assertEqual(p.read_bytes(), original)

    def test_corpus_without_candidate_does_not_fabricate_word_id(self):
        cases = [{"source_id": "place:Foo", "label": "Foo",
                  "query_name": "foo", "key_references": ["78005026"],
                  "only_mentioned_in_apocrypha": True}]
        result = mod.triage(cases, {})
        self.assertEqual(result["cases"][0]["status"],
                         "apocrypha_not_in_pinned_66_book_corpora")
        self.assertEqual(result["cases"][0]["matching_source_words"], [])

    def test_name_normalization_is_not_identity_equivalence(self):
        self.assertEqual(mod.normalize_name("Éphraïm"), "ephraim")
        self.assertEqual(mod.normalize_name("Ain (of Simeon)"), "ain of simeon")
        self.assertFalse(mod.triage(
            [{"source_id": "place:Unrelated", "label": "Aijalon",
              "query_name": "aijalon", "key_references": ["07012012"],
              "only_mentioned_in_apocrypha": False}],
            {"07012012": [{"word_id": "o070120120081",
                           "english": "Elon", "gloss": "judge",
                           "lemma": "אלון", "text": "אֵילוֹן"}]})
            ["cases"][0]["matching_source_words"])


if __name__ == "__main__":
    unittest.main()
