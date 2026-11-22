#!/usr/bin/env python3
"""Reduce inherited display-only ACAI labels to one working-language record.

BRSI identification uses source IDs, original-language word witnesses, verse
references and reviewed relations; an English short working label is kept.
This tool refuses to drop any unexpected non-English localization metadata.
The original translations remain in the pinned ACAI source and Git history.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ("deities", "fauna", "flora", "groups", "people", "places", "realia", "works")
WORKING_LANGUAGE = "eng"
REDUNDANT_FIELDS = frozenset({"preferred_label"})


def prune_record(original: dict) -> tuple[dict, int]:
    if not isinstance(original, dict) or not isinstance(original.get("bsi"), dict):
        raise ValueError("Missing BRSI record provenance")
    localizations = original.get("localizations")
    if not isinstance(localizations, dict):
        raise ValueError("Invalid localizations")
    english = localizations.get(WORKING_LANGUAGE)
    if (not isinstance(english, dict)
            or not isinstance(english.get("preferred_label"), str)
            or not english["preferred_label"].strip()):
        raise ValueError("Missing English working name; cannot prune other names safely")
    hold = original["bsi"].get("inherited_localizations", {})
    if isinstance(hold, dict):
        for selector in hold.get("fields", []):
            if "." in selector and selector.split(".", 1)[0] != WORKING_LANGUAGE:
                raise ValueError(f"Unresolved language-scoped field hold: {selector}")
    updated = copy.deepcopy(original)
    count = 0
    for language, fields in localizations.items():
        if language == WORKING_LANGUAGE:
            continue
        if not isinstance(fields, dict) or set(fields) != REDUNDANT_FIELDS:
            raise ValueError(f"Unexpected retained localization fields for {language}")
        label = fields["preferred_label"]
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Non-English localization has unexpected label for {language}")
        del updated["localizations"][language]
        count += 1
    return updated, count


def process(data: Path, categories: tuple[str, ...], *,
            write: bool = False, check: bool = False) -> dict:
    if not categories or len(set(categories)) != len(categories) or not set(categories).issubset(CATEGORIES):
        raise ValueError("Provide distinct, approved BRSI categories; Key Terms excluded")
    if write and check:
        raise ValueError("Cannot write and check simultaneously")
    counts = {}
    pending = []
    for category in categories:
        root = data / "entities" / category
        if not root.is_dir():
            raise FileNotFoundError(root)
        total = {"scanned": 0, "changed": 0, "redundant_labels_removed": 0}
        for path in sorted(root.glob("*.json")):
            original = json.loads(path.read_text(encoding="utf-8"))
            cleaned, removed = prune_record(original)
            total["scanned"] += 1
            total["redundant_labels_removed"] += removed
            if cleaned != original:
                total["changed"] += 1
                if check:
                    raise ValueError(f"Redundant inherited non-English label remains: {path}")
                pending.append((path, cleaned))
        counts[category] = total
    # Reject a bad source field in ANY selected record before touching files.
    if write:
        for path, cleaned in pending:
            path.write_text(json.dumps(cleaned, ensure_ascii=False,
                                       sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    return {"schema_version": 1, "working_language": WORKING_LANGUAGE,
            "mode": "write" if write else "check" if check else "dry_run",
            "categories": counts,
            "totals": {field: sum(row[field] for row in counts.values())
                       for field in ("scanned", "changed", "redundant_labels_removed")}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--categories", nargs="+", required=True, choices=CATEGORIES)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(process(args.data, tuple(args.categories),
                             write=args.write, check=args.check), sort_keys=True))


if __name__ == "__main__":
    main()
