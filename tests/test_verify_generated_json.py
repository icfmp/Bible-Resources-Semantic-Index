#!/usr/bin/env python3
"""Negative and positive tests for reusable strict JSON baseline comparisons."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_generated_json.py"
spec = importlib.util.spec_from_file_location("brsi_json_baseline", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerifyJsonBaselineTests(unittest.TestCase):
    def test_same_values_different_formatting_and_key_order(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Path(directory) / "generated.json"
            b = Path(directory) / "baseline.json"
            a.write_text('{"b":[{"x":1}],"a":"א"}\n', encoding="utf-8")
            b.write_text(' { "a":"א", "b": [ { "x": 1 } ] }', encoding="utf-8")
            result = module.verify(a, b)
            self.assertEqual(result["status"], "identical_strict_json_values")
            self.assertFalse(result["publication_approved"])
            self.assertNotEqual(result["generated_sha256"], result["baseline_sha256"])

    def test_absent_baseline_is_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = root / "generated.json"
            a.write_text('{}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing committed baseline"):
                module.verify(a, root / "not-committed.json")

    def test_changes_and_json_type_drift_are_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "generated.json", root / "baseline.json"
            for generated, baseline in [
                ('{"entry":"G1"}', '{"entry":"G2"}'),
                ('{"word_id":1}', '{"word_id":"1"}'),
                ('{"enabled":true}', '{"enabled":1}'),
                ('{"count":1.0}', '{"count":1}'),
            ]:
                a.write_text(generated, encoding="utf-8")
                b.write_text(baseline, encoding="utf-8")
                with self.subTest(generated=generated), self.assertRaisesRegex(
                    ValueError, "differs from committed"
                ):
                    module.verify(a, b)

    def test_duplicates_nan_and_self_comparison_are_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "generated.json", root / "baseline.json"
            b.write_text('{}', encoding="utf-8")
            for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
                a.write_text(raw, encoding="utf-8")
                with self.subTest(raw=raw), self.assertRaisesRegex(
                    ValueError, "invalid strict JSON"
                ):
                    module.verify(a, b)
            with self.assertRaisesRegex(ValueError, "different files"):
                module.verify(b, b)


if __name__ == "__main__":
    unittest.main()
