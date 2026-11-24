"""Prove the independently pinned NT index detects false Aquifer target-id reuse."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "aquifer_calibration", ROOT / "scripts" / "calibrate_aquifer_lsg_target_ids.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TargetSelectorCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.gold = {
            "format": "brsi-curated-translation-word-index-candidate",
            "curated_osis_sha256": "a" * 64,
            "source_alignment_revision": "b" * 40,
            "coverage": {"surface_word_position_candidate": 2},
            "rows": [
                {"original_ordinal": 0,
                 "original_macula_ids": ["n40001001001"],
                 "original_target_ids": ["40001001001"],
                 "status": "surface_word_position_candidate",
                 "curated_bcv": "40001001",
                 "curated_diagnostic_word_ordinal": 1},
                {"original_ordinal": 1,
                 "original_macula_ids": ["n40001001002"],
                 "original_target_ids": ["40001001003"],
                 "status": "surface_word_position_candidate",
                 "curated_bcv": "40001001",
                 "curated_diagnostic_word_ordinal": 2},
                {"original_ordinal": 2,
                 "original_macula_ids": ["n40001001003"],
                 "original_target_ids": ["40001001099"],
                 "status": "unresolved", "curated_bcv": None,
                 "curated_diagnostic_word_ordinal": None},
            ],
        }
        self.other = {
            "format": "brsi-original-and-independent-word-corroboration-candidate",
            "curated_osis_sha256": "a" * 64,
            "source_clear_bible_revision": "b" * 40,
            "source_aquifer_revision": "c" * 40,
            "original_group_counts": {"nt": 3},
            "rows": [
                {"canon": "nt", "original_ordinal": 0,
                 "original_macula_ids": ["n40001001001"],
                 "original_clear_bible_target_ids": ["40001001001"],
                 "original_target_word_witness_ids": ["40001001:1"],
                 "aquifer_source_word_witness_ids": ["40001001:1"]},
                {"canon": "nt", "original_ordinal": 1,
                 "original_macula_ids": ["n40001001002"],
                 "original_clear_bible_target_ids": ["40001001003"],
                 "original_target_word_witness_ids": ["40001001:3"],
                 "aquifer_source_word_witness_ids": ["40001001:2"]},
                {"canon": "nt", "original_ordinal": 2,
                 "original_macula_ids": ["n40001001003"],
                 "original_clear_bible_target_ids": ["40001001099"],
                 "original_target_word_witness_ids": [],
                 "aquifer_source_word_witness_ids": []},
            ],
        }

    def test_calibrates_target_positions_not_numeric_id_equality(self):
        out = mod.calibrate(self.gold, self.other)
        self.assertEqual(out["counts"], {
            "aquifer_original_macula_id_same_word": 2,
            "aquifer_same_original_target_id_exact_word": 1,
            "aquifer_same_original_target_id_wrong_word": 1,
            "original_nt_exact_french_word_candidates": 2,
            "original_nt_word_mapping_unresolved": 1,
        })
        self.assertEqual(len(out["examples"]), 1)
        self.assertEqual(out["examples"][0]["expected_bcv_word"], "40001001:2")
        self.assertFalse(out["target_id_equivalence_assumed"])

    def test_rejects_edition_and_original_id_mutation(self):
        self.other["curated_osis_sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "edition mismatch"):
            mod.calibrate(self.gold, self.other)
        self.other["curated_osis_sha256"] = "a" * 64
        self.other["rows"][1]["original_clear_bible_target_ids"] = ["40001001004"]
        with self.assertRaisesRegex(ValueError, "unaligned NT original"):
            mod.calibrate(self.gold, self.other)

    def test_unresolved_does_not_create_fake_target_mapping(self):
        self.other["rows"][0]["original_target_word_witness_ids"] = []
        out = mod.calibrate(self.gold, self.other)
        self.assertEqual(out["counts"]["aquifer_original_target_id_not_located"], 1)
        self.assertEqual(out["counts"]["aquifer_same_original_target_id_wrong_word"], 1)


if __name__ == "__main__":
    unittest.main()
