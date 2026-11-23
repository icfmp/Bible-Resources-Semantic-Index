#!/usr/bin/env python3
"""Read-only, text-free diagnostic of edition-specific translation token gaps.

Requires the original-byte-pinned candidate producer and target TSV witnesses.
Describes missing translation selectors and cross-verse patterns, never repairs them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def _ids(path: Path, pin: dict) -> set[str]:
    raw = path.read_bytes()
    if len(raw) != pin["size"] or hashlib.sha256(raw).hexdigest() != pin["sha256"]:
        raise ValueError(f"target witness differs from manifest: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or not ({"id", "identifier"} & set(reader.fieldnames)):
            raise ValueError(f"target witness lacks ID column: {path}")
        col = "id" if "id" in reader.fieldnames else "identifier"
        result: set[str] = set()
        for row in reader:
            token = row.get(col)
            if not token or token in result:
                raise ValueError(f"empty or duplicate target token ID in {path}")
            result.add(token)
    return result


def _ordinal(identifier: str) -> tuple[int, int]:
    digits = identifier[8:]
    if len(digits) not in (3, 4) or not digits.isdigit():
        raise ValueError(f"invalid target ordinal: {identifier}")
    return int(digits[:3]), int(digits[3:]) if len(digits) == 4 else 0


def _ordered(counter: Counter) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))


def diagnose(index: dict, target_ids: set[str]) -> dict:
    """Derive descriptive, noncorrective gap classes from original selector IDs."""
    canon = index["canon"]
    if canon not in ("ot", "nt") or index.get("format") != "brsi-translation-alignment-candidate":
        raise ValueError("unsupported candidate format or canon")
    coverage = index["coverage"]
    if bool(target_ids) != coverage["target_census_complete"]:
        raise ValueError("target TSV completeness disagrees with candidate")
    by_verse: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for target in target_ids:
        if len(target) not in (11, 12) or not target.isdigit():
            raise ValueError("invalid target inventory selector")
        by_verse[target[:8]].add(_ordinal(target))

    missing = Counter()
    missing_by_book = Counter()
    cross = Counter()
    cross_by_book = Counter()
    deltas = Counter()
    chapter_shifts = Counter()
    pairs = Counter()
    counted_missing = counted_cross = 0
    for row in index["records"]:
        problems = row["problems"]
        source = row["source_lookup_ids"]
        target = row["target_lookup_ids"]
        if "target_token_unattested" in problems:
            counted_missing += 1
            if not target_ids:
                raise ValueError("missing-target claim without inventory")
            absent = [t for t in target if t not in target_ids]
            if not absent:
                raise ValueError("unattested status without missing target")
            for t in absent:
                if not isinstance(t, str):
                    raise ValueError("non-token missing target")
                ordinals = by_verse.get(t[:8])
                if not ordinals:
                    kind = "target_verse_absent"
                elif _ordinal(t) < min(ordinals):
                    kind = "below_target_verse_span"
                elif _ordinal(t) > max(ordinals):
                    kind = "above_target_verse_span"
                else:
                    kind = "gap_within_target_verse_span"
                missing[kind] += 1
                missing_by_book[t[:2]] += 1
        if "cross_verse_selector" in problems:
            counted_cross += 1
            if not source or not target or any(not isinstance(x, str) for x in source + target):
                raise ValueError("cross-verse row lacks valid IDs")
            for s in {v[1:9] for v in source}:
                for t in {v[:8] for v in target}:
                    if s[:2] != t[:2]:
                        kind = "different_book"
                    elif s[2:5] != t[2:5]:
                        kind = "different_chapter"
                    elif s[5:8] != t[5:8]:
                        kind = "different_verse_same_chapter"
                    else:
                        kind = "same_verse_in_multiverse_group"
                    cross[kind] += 1
                    cross_by_book[s[:2]] += 1
                    pairs[f"{s}>{t}"] += 1
                    if kind == "different_verse_same_chapter":
                        delta = int(t[5:8]) - int(s[5:8])
                        deltas[f"{delta:+d}"] += 1
                        chapter_shifts[f"{s[:5]}:{delta:+d}"] += 1
    if counted_missing != coverage.get("problem_target_token_unattested", 0):
        raise ValueError("missing-target count disagrees with producer")
    if counted_cross != coverage.get("problem_cross_verse_selector", 0):
        raise ValueError("cross-verse count disagrees with producer")
    return {
        "canon": canon,
        "records": len(index["records"]),
        "target_inventory_present": bool(target_ids),
        "unattested_target_records": counted_missing,
        "unattested_target_selectors": sum(missing.values()),
        "unattested_target_classes": _ordered(missing),
        "unattested_target_by_book": _ordered(missing_by_book),
        "cross_verse_records": counted_cross,
        "cross_verse_reference_pairs": sum(pairs.values()),
        "distinct_cross_verse_pairs": len(pairs),
        "cross_verse_classes": _ordered(cross),
        "cross_verse_by_source_book": _ordered(cross_by_book),
        "same_chapter_verse_deltas": _ordered(deltas),
        "largest_same_chapter_clusters": [
            {"source_book_chapter_and_delta": key, "records": count}
            for key, count in sorted(chapter_shifts.items(), key=lambda x: (-x[1], x[0]))[:25]
        ],
        "largest_cross_verse_pairs": [
            {"source_to_target_bcv": key, "records": count}
            for key, count in sorted(pairs.items(), key=lambda x: (-x[1], x[0]))[:25]
        ],
        "all_target_tokens_editorially_verified": False,
        "versification_corrections_inferred": 0,
    }


def audit(candidate_dir: Path, manifest: dict, upstream_root: Path) -> dict:
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported source manifest")
    filepins = {item["key"]: item for item in manifest["inputs"]}
    receipt = json.loads((candidate_dir / "receipt.json").read_text(encoding="utf-8"))
    if receipt["upstream_revision"] != manifest["revision"] or receipt["publication_approved"] is not False:
        raise ValueError("revision mismatch or public receipt")
    groups = {}
    for group in manifest["groups"]:
        canon = group["canon"]
        if canon in groups:
            raise ValueError("duplicate canon")
        pin = filepins[group["target"]]
        if ".." in Path(pin["path"]).parts or Path(pin["path"]).is_absolute():
            raise ValueError("unsafe target witness path")
        path = upstream_root / pin["path"]
        target_ids = _ids(path, pin)
        raw = (candidate_dir / (canon + ".json")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt["candidate_outputs"][canon]["sha256"]:
            raise ValueError("candidate JSON differs from receipt")
        index = json.loads(raw)
        if index["canon"] != canon or index["upstream_revision"] != manifest["revision"]:
            raise ValueError("candidate source edition mismatch")
        groups[canon] = diagnose(index, target_ids)
    return {
        "schema_version": 1,
        "audit_kind": "descriptive-translation-token-gap-triage",
        "upstream_revision": manifest["revision"],
        "edition_or_word_identity_certified": False,
        "publication_approved": False,
        "groups": groups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--upstream-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.candidate_dir, json.loads(args.manifest.read_text()), args.upstream_root)
    data = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    args.output.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
