#!/usr/bin/env python3
"""Prevent weaker Greek contextual source defaults from overwriting original LN."""
import inspect,runpy,unittest
from pathlib import Path
M=runpy.run_path(str(Path(__file__).with_name("build_lower_confidence_single_sense.py")))
class GreekLowerConfidenceEditorialTests(unittest.TestCase):
    def test_170_cases_provenance_pinned(self):
        self.assertEqual(sum(M["SOURCE_CATEGORIES"].values()),170)
        self.assertEqual(len(M["SOURCE_CATEGORIES"]),2)
    def test_single_ubs_lexid_never_treated_as_proven_contextual_meaning(self):
        src=inspect.getsource(M["build"])
        self.assertIn("LOWER_CONFIDENCE_PROVISIONAL",src)
        self.assertIn("verse_context_semantically_verified",src)
        self.assertIn("original_ln",src)
        self.assertIn("set(original_ln.split())&set(source_codes)",src)
        self.assertIn("original_macula_ln_changed",src)
    def test_all_source_lexid_authorizations_are_explicit(self):
        self.assertEqual(M["SOURCE_CATEGORIES"]["blank_MACULA_original_LN__exactly_one_original_UBS_LEXID_without_matching_word_LN_NOT_APPROVED"],120)
        self.assertEqual(M["SOURCE_CATEGORIES"]["nonblank_MACULA_LN_not_attested_under_UBS_headword__exactly_one_original_UBS_LEXID_without_matching_word_LN_NOT_APPROVED"],50)

    def test_full_unresolved_source_partition_runs_inside_builder(self):
        # A separate intermediate priorities JSON is not an independent
        # review: the source-specific classification is now mandatory here.
        from unittest.mock import patch
        with patch.dict(M["build"].__globals__["AUDIT"], {
            "audit": lambda *args: (_ for _ in ()).throw(
                ValueError("source priority census invoked"))}):
            with self.assertRaisesRegex(ValueError,"source priority census invoked"):
                M["build"]({}, [], [])


if __name__=="__main__":unittest.main()
