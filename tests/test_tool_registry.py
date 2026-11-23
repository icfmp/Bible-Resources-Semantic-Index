#!/usr/bin/env python3
"""Regression tests for source-neutral, non-destructive tooling inventory."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool_registry.py"
spec = importlib.util.spec_from_file_location("brsi_tool_registry", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ToolInventoryTests(unittest.TestCase):
    def make(self, root: Path, name: str, text: str = "") -> None:
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")

    def test_workflow_literal_and_glob_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make(root, "scripts/build.py", "pass")
            self.make(root, "links/dictionaries/example/test_source.py", "pass")
            self.make(root, ".github/workflows/pinned.yml",
                      "run: python3 -I scripts/build.py\n"
                      "tests=(links/dictionaries/example/test_*.py)\n")
            refs, missing = mod.workflow_references(root)
            self.assertEqual(missing, [])
            self.assertIn(".github/workflows/pinned.yml", refs["scripts/build.py"])
            self.make(root, ".github/workflows/pinned.yml",
                      "run: python3 -I scripts/missing.py\n")
            _, missing = mod.workflow_references(root)
            self.assertEqual(missing, [{"workflow": ".github/workflows/pinned.yml",
                                        "path": "scripts/missing.py"}])

    def test_source_local_runpy_is_not_assumed_dead(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make(root, "links/dictionaries/example/verify.py",
                      "def verify(): return True\n")
            self.make(root, "links/dictionaries/example/build.py",
                      'from pathlib import Path\n'
                      'mod = Path(__file__).with_name("verify.py")\n')
            report = mod.inventory(root)
            target = next(x for x in report["tools"]
                          if x["path"] == "links/dictionaries/example/verify.py")
            self.assertEqual(target["scope"], "source_specific")
            self.assertIn("links/dictionaries/example/build.py",
                          target["references"]["code"])
            self.assertFalse(target["manual_caller_review_required"])

    def test_test_constructing_shared_path_counts_as_caller(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make(root, "scripts/resolve.py", "pass\\n")
            self.make(root, "tests/test_resolve.py",
                      'file = root / "scripts" / "resolve.py"\\n')
            result = mod.inventory(root)
            row = next(x for x in result["tools"] if x["path"] == "scripts/resolve.py")
            self.assertEqual(row["references"]["tests"], ["tests/test_resolve.py"])
            self.assertFalse(row["manual_caller_review_required"])

    def test_no_reference_is_only_manual_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make(root, "scripts/unused.py", "pass\n")
            result = mod.inventory(root)
            self.assertEqual(len(result["tools"]), 1)
            self.assertTrue(result["tools"][0]["manual_caller_review_required"])


if __name__ == "__main__":
    unittest.main()
