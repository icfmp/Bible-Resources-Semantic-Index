#!/usr/bin/env python3
"""Negative and positive checks for the read-only repository hygiene gate."""
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "scripts" / "check_repository_hygiene.py"
spec = importlib.util.spec_from_file_location("brsi_repository_hygiene", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write(root: Path, name: str, text: str = "") -> None:
    file = root / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   stderr=subprocess.STDOUT).decode().strip()


def commit(root: Path) -> None:
    git(root, "add", ".")
    git(root, "-c", "user.name=Maintenance Tests",
        "-c", "user.email=tests@example.invalid",
        "commit", "--quiet", "-m", "synthetic fixture")


class RepositoryHygieneTests(unittest.TestCase):
    def test_ignored_transient_artifacts_and_retained_evidence(self):
        bad = [
            "scripts/__pycache__/build.cpython-312.pyc",
            "work/snapshots/source.tar.gz",
            ".pytest_cache/v/cache/stepwise",
            "tmp/output.json",
            "build/index.json",
            "dist/release.zip",
            ".cache/payload",
            "tests/notes.txt~",
            "scripts/normalize.py.orig",
            "sources/rebuild.log",
            "data/.DS_Store",
        ]
        for path in bad:
            with self.subTest(path=path):
                self.assertIsNotNone(mod.transient_reason(path))
        good = [
            "data/entities/person/Abraham.json",
            "data/source.lock.json",
            "release/historical-release.sha256",
            "links/dictionaries/ubs-greek/index.json",
            "links/dictionaries/ubs-hebrew/v1_final_word_specific_approvals.json",
            "work/README.md",
            "docs/MAINTENANCE_POLICY.md",
        ]
        for path in good:
            with self.subTest(path=path):
                self.assertIsNone(mod.transient_reason(path))

    def test_document_links_are_rooted_and_fences_not_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root, "README.md", "root")
            write(root, "docs/guide.md", "guide")
            write(root, "docs/a name.md", "with a space")
            content = (
                "[root](../README.md#section)\n"
                "[guide](./guide.md)\n"
                "[escaped](a%20name.md)\n"
                "[external](https://github.com/example/missing)\n"
                "[anchor](#section)\n"
                "~~~sh\n"
                "[example](missing-in-code.md)\n"
                "~~~\n"
            )
            self.assertEqual(
                mod.broken_local_links(root, "docs/guide.md", content), [])
            broken = mod.broken_local_links(
                root, "docs/guide.md",
                "[missing](does-not-exist.md)\n[outside](../../secret.txt)\n")
            self.assertEqual(
                {row["code"] for row in broken},
                {"broken_local_markdown_link", "link_outside_repository"})

    def test_new_tool_requires_test_not_just_docs_or_workflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root, "scripts/new_tool.py", "pass\n")
            write(root, "docs/guide.md", "Run scripts/new_tool.py\n")
            write(root, ".github/workflows/offline.yml",
                  "run: python3 scripts/new_tool.py\n")
            tracked = ["scripts/new_tool.py", "docs/guide.md",
                       ".github/workflows/offline.yml"]
            issues = mod.audit_new_tool_tests(
                root, ["scripts/new_tool.py"], tracked)
            self.assertEqual(len(issues), 1)
            self.assertEqual(
                issues[0]["code"], "new_python_tool_without_test_reference")
            write(root, "tests/test_new_tool.py",
                  'PATH = "scripts/new_tool.py"\n')
            tracked.append("tests/test_new_tool.py")
            self.assertEqual(mod.audit_new_tool_tests(
                root, ["scripts/new_tool.py"], tracked), [])

    def test_only_added_maintained_python_tools_are_checked(self):
        self.assertTrue(mod.is_maintained_python_tool(
            "links/dictionaries/ubs-greek/review_source.py"))
        self.assertTrue(mod.is_maintained_python_tool(
            "scripts/check_repository_hygiene.py"))
        for path in ("tests/test_example.py",
                     "links/dictionaries/ubs-greek/test_index.py",
                     "docs/guide.py", "scripts/report.json"):
            self.assertFalse(mod.is_maintained_python_tool(path))

    def test_real_git_base_diff_and_tracked_temp_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            git(root, "init", "--quiet")
            write(root, "README.md", "# Example\n")
            commit(root)
            base = git(root, "rev-parse", "HEAD")
            write(root, "scripts/new_tool.py", "print('hi')\n")
            write(root, "docs/new.md", "[missing](no.md)\n")
            write(root, "tmp/report.json", "{}\n")
            commit(root)
            self.assertEqual(mod.newly_added_tools(root, base),
                             ["scripts/new_tool.py"])
            report = mod.audit(root, base_sha=base)
            self.assertEqual(
                {issue["code"] for issue in report["errors"]},
                {"tracked_temporary_file",
                 "broken_local_markdown_link",
                 "new_python_tool_without_test_reference"})
            write(root, "tests/test_new_tool.py",
                  'PATH = "scripts/new_tool.py"\n')
            write(root, "docs/no.md", "# Now present\n")
            git(root, "rm", "-q", "tmp/report.json")
            commit(root)
            self.assertEqual(mod.audit(root, base_sha=base)["errors"], [])


if __name__ == "__main__":
    unittest.main()
