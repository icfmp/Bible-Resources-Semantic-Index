#!/usr/bin/env python3
"""Conservative, read-only repository hygiene checks for BRSI pull requests.

Reject deterministic problems only: tracked transient files, broken local
Markdown destinations, and newly added maintained Python tools without a
literal source-test reference. Never delete original or editorial data.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

TRANSIENT_DIRS = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".venv",
})
TOP_LEVEL_GENERATED = frozenset({
    "tmp", "dist", "build", "checkouts", ".cache",
})
TRANSIENT_NAMES = frozenset({".DS_Store", "Thumbs.db", ".coverage"})
TRANSIENT_SUFFIXES = (
    ".pyc", ".pyo", ".swp", ".swo", ".tmp", ".temp", ".log",
    ".orig", ".rej", ".tar.gz", ".tar.gz.sha256",
)
MARKDOWN_LINK = re.compile(r"\]\(\s*(<[^>]+>|[^\s)]+)")
URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FENCE = re.compile(r"^\s*((?:\x60){3,}|~{3,})")


def git_paths(root: Path, *args: str) -> list[str]:
    """Use NUL-delimited Git output to support filenames with whitespace."""
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=True,
    )
    return sorted({os.fsdecode(part) for part in result.stdout.split(b"\0")
                   if part})


def tracked_paths(root: Path) -> list[str]:
    return git_paths(root, "ls-files", "--cached", "-z")


def newly_added_tools(root: Path, base_sha: str) -> list[str]:
    """Compare a GitHub PR checkout against its fetched exact base commit."""
    added = git_paths(
        root, "diff", "--no-renames", "--diff-filter=A", "--name-only",
        "-z", base_sha, "HEAD", "--", "scripts/", "links/",
    )
    return [name for name in added if is_maintained_python_tool(name)]


def is_maintained_python_tool(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        path.suffix == ".py"
        and not path.name.startswith("test_")
        and bool(path.parts)
        and path.parts[0] in {"scripts", "links"}
    )


def transient_reason(name: str) -> str | None:
    path = PurePosixPath(name)
    if any(part in TRANSIENT_DIRS for part in path.parts[:-1]):
        return "tracked cache or virtual environment"
    if path.parts and path.parts[0] in TOP_LEVEL_GENERATED:
        return "tracked generated checkout or local build directory"
    if path.parts[:2] == ("work", "snapshots"):
        return "tracked restricted temporary source snapshot"
    if path.name in TRANSIENT_NAMES:
        return "tracked local or machine-generated file"
    if path.name.endswith(TRANSIENT_SUFFIXES) or path.name.endswith("~"):
        return "tracked temporary or generated output"
    return None


def prose_without_fences(content: str) -> str:
    """Ignore fenced code examples, not navigational Markdown."""
    pieces = []
    opened: tuple[str, int] | None = None
    for line in content.splitlines(keepends=True):
        fence = FENCE.match(line)
        if opened is None:
            if fence:
                opened = (fence.group(1)[0], len(fence.group(1)))
                pieces.append("\n")
            else:
                pieces.append(line)
        elif (fence and fence.group(1)[0] == opened[0]
              and len(fence.group(1)) >= opened[1]):
            opened = None
            pieces.append("\n")
        else:
            pieces.append("\n")
    return "".join(pieces)


def local_link_target(link: str) -> str | None:
    """Ignore external URLs and anchor-only links; check local paths only."""
    if link.startswith("<") and link.endswith(">"):
        link = link[1:-1]
    link = link.strip()
    if not link or link.startswith(("#", "//")) or URL_SCHEME.match(link):
        return None
    path = unquote(urlsplit(link).path)
    return path or None


def broken_local_links(root: Path, name: str, content: str) -> list[dict]:
    issues = []
    source = root / name
    root_resolved = root.resolve()
    for match in MARKDOWN_LINK.finditer(prose_without_fences(content)):
        raw = match.group(1)
        target = local_link_target(raw)
        if target is None:
            continue
        # Root-relative Markdown paths refer to the repository root.
        absolute = ((root / target.lstrip("/")) if target.startswith("/")
                    else (source.parent / target))
        resolved = absolute.resolve(strict=False)
        if not resolved.is_relative_to(root_resolved):
            issues.append({"code": "link_outside_repository", "path": name,
                           "detail": raw})
        elif not resolved.exists():
            issues.append({"code": "broken_local_markdown_link", "path": name,
                           "detail": raw})
    return issues


def audit_new_tool_tests(root: Path, new_tools: list[str],
                         tracked: list[str]) -> list[dict]:
    """A new tool needs a source-local test, not an inferred deletion rule.

    Literal filename references are only a coverage signal; reviewers still
    check that the test meaningfully verifies the new behavior.
    """
    tests = [
        name for name in tracked if name.endswith(".py")
        and PurePosixPath(name).name.startswith("test_")
        and name.startswith(("tests/", "links/"))
    ]
    contents = {(root / name).read_text(encoding="utf-8", errors="replace")
                for name in tests}
    issues = []
    for path in new_tools:
        basename = PurePosixPath(path).name
        if not any(path in text or basename in text for text in contents):
            issues.append({
                "code": "new_python_tool_without_test_reference",
                "path": path,
                "detail": "Add a regression test referencing this tool; "
                          "document exceptional manual use in the PR.",
            })
    return issues


def audit(root: Path, *, base_sha: str | None = None) -> dict:
    tracked = tracked_paths(root)
    issues = []
    for name in tracked:
        reason = transient_reason(name)
        if reason:
            issues.append({"code": "tracked_temporary_file",
                           "path": name, "detail": reason})
        if name.endswith(".md"):
            content = (root / name).read_text(encoding="utf-8",
                                              errors="replace")
            issues.extend(broken_local_links(root, name, content))
    new_tools: list[str] = []
    if base_sha:
        new_tools = newly_added_tools(root, base_sha)
        issues.extend(audit_new_tool_tests(root, new_tools, tracked))
    return {
        "schema": "brsi.repository-hygiene.v1",
        "tracked_files_checked": len(tracked),
        "markdown_files_checked": sum(name.endswith(".md") for name in tracked),
        "new_tools_checked": new_tools,
        "errors": sorted(issues, key=lambda e: (e["path"], e["code"], e["detail"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--base-sha", default="",
                        help="Optional checked-out PR base commit SHA")
    parser.add_argument("--json", action="store_true",
                        help="Print read-only machine-readable results")
    args = parser.parse_args()
    try:
        report = audit(args.root.resolve(), base_sha=args.base_sha or None)
    except (OSError, subprocess.CalledProcessError) as exc:
        print("BRSI_HYGIENE_UNABLE_TO_VERIFY", str(exc))
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("BRSI_HYGIENE", "tracked", report["tracked_files_checked"],
              "markdown", report["markdown_files_checked"],
              "new_tools", len(report["new_tools_checked"]),
              "errors", len(report["errors"]))
        for issue in report["errors"]:
            print("BRSI_HYGIENE_ERROR", issue["code"],
                  issue["path"], issue["detail"])
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
