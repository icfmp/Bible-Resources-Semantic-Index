"""No falsely inferred French word links from orthographic audit classes."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_fr_variant_audit", ROOT / "scripts" / "audit_curated_lsg_surface_variants.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SourceOnlyOrthographyAuditTests(unittest.TestCase):
    def check(self, source: str, authored: list[str], expected: str,
              original: list[str] | None = None):
        status, word = audit.classify_absent_french_target(
            source, original if original is not None else [source], authored)
        self.assertEqual(status, expected)
        if expected.endswith("_only") or expected == "case_and_ligature":
            self.assertIsNotNone(word)

    def test_strict_nfc_case_ligature_and_accents_are_separate_diagnostics(self):
        self.check("Dieu", ["dieu"], "case_only")
        self.check("oeuvre", ["œuvre"], "ligature_only")
        self.check("œuvre", ["Oeuvre"], "case_and_ligature")
        self.check("eleve", ["élève"], "accent_only")
        self.check("l'amour", ["l’amour"], "apostrophe_only")
        self.check("montagne", ["montagne"], "same_surface_not_located_or_repeated")
        self.check("mon", ["ton"], "no_strict_orthographic_candidate")
        self.check("un mot", ["un", "mot"], "no_strict_orthographic_candidate")

    def test_diagnostic_never_chooses_repeated_words_or_ambiguous_source(self):
        self.check("Dieu", ["dieu", "dieu"],
                   "normalized_candidate_ambiguous")
        self.check("Dieu", ["dieu"],
                   "normalized_candidate_ambiguous", original=["Dieu", "dieu"])
        self.check("eleve", ["élève", "élève"],
                   "normalized_candidate_ambiguous")
        self.check("oeuvre", ["œuvre", "œuvre"],
                   "normalized_candidate_ambiguous")

    def test_original_aquifer_ids_are_read_not_generated(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            chapter = root / "fra" / "alignments" / "json"
            chapter.mkdir(parents=True)
            original = {
                "format": "alignment",
                "groups": [{
                    "type": "translation",
                    "documents": [{"docid": "WLCM"}, {"docid": "LSG"}],
                    "records": [
                        {"source": ["010010010011|אֱלֹהִים"],
                         "target": ["01001001001|Dieu"]},
                        {"source": ["010010010021|מְלָאכָה"],
                         "target": ["01001001002|oeuvre"]},
                    ],
                    "meta": {"nonEquivalent": {"source": [],
                                               "target": ["01001001003|autre"]}},
                }],
            }
            (chapter / "01-001.alignment.json").write_text(
                json.dumps(original, ensure_ascii=False), encoding="utf-8")
            result = audit.audit_target_surfaces(
                root, {"01001001": "dieu œuvre autre"},
                {
                    "o010010010011": "exact_french_word_absent_from_curated_verse",
                    "o010010010021": "exact_french_word_absent_from_curated_verse",
                })
            self.assertEqual(result["original_unlinked_exact_word_absence_total"], 2)
            self.assertEqual(result["by_canon"]["ot"], {
                "case_only": 1, "ligature_only": 1})
            self.assertEqual(result["source_ids_by_diagnostic"], {
                "o010010010011": "case_only",
                "o010010010021": "ligature_only",
            })
            self.assertFalse(result["linguistic_links_automatically_approved"])
            self.assertFalse(result["source_french_text_modified"])

    def test_missing_original_alignment_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                audit.audit_target_surfaces(
                    Path(folder), {"01001001": "dieu"},
                    {"o010010010011": "exact_french_word_absent_from_curated_verse"})


if __name__ == "__main__":
    unittest.main()
