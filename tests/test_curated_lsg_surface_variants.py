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

    def test_neighboring_verse_exact_word_is_diagnostic_not_remap(self):
        verses = {
            "01001001": "Dieu parle",
            "01001002": "Un autre mot",
            "01001003": "Dieu aussi",
            "01002001": "Dieu dans un autre chapitre",
        }
        cache = {}
        self.assertEqual(audit.neighboring_verse_context(
            "Dieu", "01001002", verses, cache),
            "exact_word_in_both_adjacent_verses")
        del verses["01001003"]
        self.assertEqual(audit.neighboring_verse_context(
            "Dieu", "01001002", verses, cache),
            "exact_word_in_previous_verse")
        self.assertEqual(audit.neighboring_verse_context(
            "Dieu", "01001003", verses, cache),
            "no_exact_word_in_consecutive_same_chapter_verses")
        self.assertEqual(audit.neighboring_verse_context(
            "Dieu", "01001004", verses, cache),
            "no_exact_word_in_consecutive_same_chapter_verses")
        with self.assertRaisesRegex(ValueError, "invalid original"):
            audit.neighboring_verse_context(
                "Dieu", "Gen1", verses, cache)

    def test_original_source_coordinates_are_not_called_french_word_links(self):
        authored = {"01001001": "Dieu parla",
                    "01001002": "Un autre mot"}
        cache = {}
        self.assertEqual(audit.original_source_verse_context(
            "Dieu", "o010010010011", "01001002", authored, cache),
            "exact_french_word_present_at_original_source_verse_reference")
        self.assertEqual(audit.original_source_verse_context(
            "Dieu", "o010010020011", "01001002", authored, cache),
            "original_source_and_aquifer_target_verses_identical")
        self.assertEqual(audit.original_source_verse_context(
            "Dieu", "o010010030011", "01001002", authored, cache),
            "different_original_source_verse_missing_from_curated")
        self.assertEqual(audit.original_source_verse_context(
            "Dieu", "o010010010011", "01001001", authored, cache),
            "original_source_and_aquifer_target_verses_identical")

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
            self.assertEqual(result["reference_context_by_canon"]["ot"], {
                "no_exact_word_in_consecutive_same_chapter_verses": 2})
            self.assertEqual(
                result["source_coordinate_context_by_canon"]["ot"],
                {"original_source_and_aquifer_target_verses_identical": 2})
            self.assertEqual(len(result["reference_context_by_original_macula_id"]), 2)
            self.assertEqual(result["source_ids_by_diagnostic"], {
                "o010010010011": "case_only",
                "o010010010021": "ligature_only",
            })
            self.assertFalse(result["linguistic_links_automatically_approved"])
            self.assertFalse(result["source_french_text_modified"])

    def test_clear_bible_source_verse_corroboration_never_approves_translation(self):
        source = "o010010010011"
        original = {
            "format": "brsi-original-and-independent-word-corroboration-candidate",
            "by_original_macula_id": {source: [0]},
            "rows": [{
                "original_ordinal": 0,
                "original_macula_ids": [source],
                "original_clear_bible_target_ids": ["01001001001"],
            }],
        }
        result = audit.cross_check_original_source_verses_with_clear_bible(
            {source: ["01001002"]}, original)
        self.assertEqual(result["counts"], {
            "clear_bible_original_target_supports_macula_source_reference": 1})
        self.assertEqual(result["cases"][0]["macula_original_source_verse"], "01001001")
        self.assertEqual(result["cases"][0]["clear_bible_original_target_verses"],
                         ["01001001"])
        self.assertFalse(result["cases"][0]["word_translation_approved"])
        self.assertFalse(result["cases"][0]["verse_remapping_approved"])
        original["rows"][0]["original_clear_bible_target_ids"] = ["01001002001"]
        result = audit.cross_check_original_source_verses_with_clear_bible(
            {source: ["01001002"]}, original)
        self.assertEqual(result["counts"], {
            "clear_bible_original_target_supports_aquifer_target_reference": 1})
        original["rows"][0]["original_ordinal"] = None
        result = audit.cross_check_original_source_verses_with_clear_bible(
            {source: ["01001002"]}, original)
        self.assertEqual(result["counts"], {
            "clear_bible_has_no_original_alignment_record": 1})

    def test_verse_corroboration_fails_closed_on_target_identity_and_index(self):
        source = "o010010010011"
        index = {
            "format": "brsi-original-and-independent-word-corroboration-candidate",
            "by_original_macula_id": {source: [0]},
            "rows": [{
                "original_ordinal": 0,
                "original_macula_ids": [source],
                "original_clear_bible_target_ids": ["01001002001"],
            }],
        }
        with self.assertRaisesRegex(ValueError, "different source/target"):
            audit.cross_check_original_source_verses_with_clear_bible(
                {source: ["01001001"]}, index)
        index["rows"][0]["original_macula_ids"] = ["o010010010021"]
        with self.assertRaisesRegex(ValueError, "unrelated original"):
            audit.cross_check_original_source_verses_with_clear_bible(
                {source: ["01001002"]}, index)
        index["by_original_macula_id"] = {}
        with self.assertRaisesRegex(ValueError, "missing from pinned index"):
            audit.cross_check_original_source_verses_with_clear_bible(
                {source: ["01001002"]}, index)

    def test_original_source_word_is_located_elsewhere_only_as_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            chapter = root / "fra" / "alignments" / "json"
            chapter.mkdir(parents=True)
            doc = {
                "format": "alignment",
                "groups": [{
                    "type": "translation",
                    "documents": [{"docid": "WLCM"}, {"docid": "LSG"}],
                    "records": [
                        {"source": ["010010010011|מִלָּה"],
                         "target": ["01001002001|Dieu"]},
                    ],
                    "meta": {"nonEquivalent": {"source": [], "target": []}},
                }],
            }
            (chapter / "01-001.alignment.json").write_text(
                json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            report = audit.audit_target_surfaces(
                root, {"01001001": "Dieu parlait",
                       "01001002": "dieu prononça"},
                {"o010010010011":
                 "exact_french_word_absent_from_curated_verse"})
            self.assertEqual(
                report["original_source_verse_exact_word_candidate_aquifer_verses"],
                {"o010010010011": ["01001002"]})
            self.assertEqual(
                report["source_coordinate_context_by_canon"]["ot"], {
                    "exact_french_word_present_at_original_source_verse_reference": 1})
            self.assertEqual(report["reference_context_by_canon"]["ot"], {
                "exact_word_in_previous_verse": 1})
            self.assertFalse(report["linguistic_links_automatically_approved"])

    def test_missing_original_alignment_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                audit.audit_target_surfaces(
                    Path(folder), {"01001001": "dieu"},
                    {"o010010010011": "exact_french_word_absent_from_curated_verse"})


if __name__ == "__main__":
    unittest.main()
