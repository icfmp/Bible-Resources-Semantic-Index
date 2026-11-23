#!/usr/bin/env python3
"""Read-only inventory of maintained tools and literal GitHub Actions callers.

A missing static caller is a reason for human review, NOT proof that a file
can be deleted. Dynamic imports, historical tagged builds and external callers
need a separate source/rights assessment before retiring anything.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

WORKFLOW_PYTHON = re.compile(
    r"(?<![A-Za-z0-9_])((?:scripts|tests|links)/[A-Za-z0-9_./*-]+\.py)(?![A-Za-z0-9_])"
)
SOURCE_SUFFIXES = {".py", ".sh", ".cpp", ".md", ".yml", ".yaml"}
SOURCE_DIRS = ("scripts", "links", "tests", "docs", "work", "sources", "release", ".github/workflows")


def workflow_references(root: Path) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    """Check concrete/wildcard Python path literals in checked-in workflows."""
    found: dict[str, list[str]] = {}
    missing: list[dict[str, str]] = []
    workflows = root / ".github" / "workflows"
    for workflow in sorted((*workflows.glob("*.yml"), *workflows.glob("*.yaml"))):
        content = workflow.read_text(encoding="utf-8")
        for path in sorted(set(WORKFLOW_PYTHON.findall(content))):
            rel = workflow.relative_to(root).as_posix()
            found.setdefault(path, []).append(rel)
            if not list(root.glob(path)):
                missing.append({"workflow": rel, "path": path})
    return found, missing


def code_and_document_sources(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for folder in SOURCE_DIRS:
        base = root / folder
        if base.is_dir():
            paths.update(p for p in base.rglob("*")
                         if p.is_file() and p.suffix in SOURCE_SUFFIXES)
    paths.update(p for p in (root / "README.md", root / "CONTRIBUTING.md")
                 if p.is_file())
    return sorted(paths)


def maintained_tools(root: Path) -> list[Path]:
    """Shared scripts and source-owned non-test Python helpers."""
    base = root / "scripts"
    tools = set()
    if base.is_dir():
        tools.update(p for p in base.rglob("*")
                     if p.is_file() and p.suffix in {".py", ".sh", ".cpp"}
                     and not p.name.startswith("test_"))
    links = root / "links"
    if links.is_dir():
        tools.update(p for p in links.rglob("*.py")
                     if not p.name.startswith("test_"))
    return sorted(tools)


def inventory(root: Path) -> dict:
    candidates = maintained_tools(root)
    sources = code_and_document_sources(root)
    texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in sources}
    workflow_refs, missing = workflow_references(root)
    rows = []
    for candidate in candidates:
        target = candidate.relative_to(root).as_posix()
        groups = {"workflows": set(), "code": set(), "tests": set(),
                  "documentation": set()}
        for caller, content in texts.items():
            if caller == candidate:
                continue
            rel = caller.relative_to(root).as_posix()
            # Match literal full path or same-directory basename (e.g. runpy
            # Path(__file__).with_name("foo.py")). These are hints, not proofs.
            if target not in content and not (
                caller.parent == candidate.parent and candidate.name in content
            ):
                continue
            category = ("workflows" if rel.startswith(".github/workflows/")
                        else "documentation" if caller.suffix == ".md"
                        else "tests" if caller.name.startswith("test_")
                        or rel.startswith("tests/")
                        else "code")
            groups[category].add(rel)
        groups["workflows"].update(workflow_refs.get(target, ()))
        direct = {key: sorted(value) for key, value in groups.items()}
        rows.append({
            "path": target,
            "scope": "shared" if target.startswith("scripts/") else "source_specific",
            "references": direct,
            # Do not label an unreferenced tool obsolete automatically.
            "manual_caller_review_required": not bool(
                groups["workflows"] or groups["code"] or groups["tests"]
            ),
        })
    return {"schema": "brsi.tool-inventory.v1", "tools": rows,
            "missing_workflow_python_paths": missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--check-workflows", action="store_true",
                        help="fail on workflow references to missing Python files")
    parser.add_argument("--json", action="store_true",
                        help="print full source/caller inventory")
    args = parser.parse_args()
    report = inventory(args.root.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print("BRSI_TOOLS", len(report["tools"]),
              "MISSING_WORKFLOW_PYTHON_PATHS",
              len(report["missing_workflow_python_paths"]),
              "MANUAL_CALLER_REVIEWS",
              sum(x["manual_caller_review_required"] for x in report["tools"]))
        for row in report["missing_workflow_python_paths"]:
            print("MISSING_WORKFLOW_SCRIPT", row["workflow"], row["path"])
    return int(args.check_workflows and bool(report["missing_workflow_python_paths"]))


if __name__ == "__main__":
    raise SystemExit(main())
