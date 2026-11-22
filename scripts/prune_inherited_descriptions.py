#!/usr/bin/env python3
"""Remove inherited ACAI encyclopedia prose from current BRSI entity records.

Only localizations.*.descriptions and description-only editorial holds change.
Original sources remain recoverable from pinned ACAI commits and source hashes.
The default action is a dry run; explicit --write is required for changes.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ("deities", "fauna", "flora", "groups", "people", "places", "realia", "works")


def prune_record(source: dict) -> tuple[dict, int, int, bool]:
    """Return (updated record, removed rows, removed fields, removed holds).

    Never infer an identifying label, discard a different localization field,
    edit original word IDs, or alter review receipts.
    """
    if not isinstance(source, dict) or not isinstance(source.get("bsi"), dict):
        raise ValueError("Expected a BRSI record with provenance")
    result = copy.deepcopy(source)
    original_localizations = result.get("localizations", {})
    if not isinstance(original_localizations, dict):
        raise ValueError("Invalid inherited localizations")
    rows = fields = 0
    for lang, localized in original_localizations.items():
        if not isinstance(localized, dict):
            raise ValueError(f"Invalid localization for {lang}")
        if "descriptions" not in localized:
            continue
        value = localized["descriptions"]
        if not isinstance(value, list):
            raise ValueError(f"Unsupported descriptions type for {lang}")
        rows += len(value)
        fields += 1
        del localized["descriptions"]
    # The inherited provenance still lives in bsi.source_id/source_sha256
    # and the frozen upstream snapshot, rather than a duplicate prose archive.
    meta = result["bsi"]
    hold_removed = False
    hold = meta.get("inherited_localizations")
    if isinstance(hold, dict) and "descriptions" in hold.get("fields", []):
        remaining = [f for f in hold["fields"] if f != "descriptions"]
        if remaining:
            hold["fields"] = remaining
        else:
            del meta["inherited_localizations"]
        hold_removed = True
    return result, rows, fields, hold_removed


def process(data: Path, categories: tuple[str, ...], *, write: bool = False,
            check: bool = False) -> dict:
    if not categories or len(set(categories)) != len(categories):
        raise ValueError("Provide unique explicit categories")
    if write and check:
        raise ValueError("--write and --check are mutually exclusive")
    if not set(categories).issubset(CATEGORIES):
        raise ValueError("Unknown category or restricted Key Terms")
    counts = {}
    total = {"records_scanned": 0, "records_changed": 0,
             "description_rows_removed": 0, "description_fields_removed": 0,
             "description_holds_cleared": 0}
    pending = []
    for category in categories:
        directory = data / "entities" / category
        if not directory.is_dir():
            raise FileNotFoundError(directory)
        category_count = {k: 0 for k in total}
        for path in sorted(directory.glob("*.json")):
            original_bytes = path.read_bytes()
            original = json.loads(original_bytes)
            cleaned, rows, fields, holds = prune_record(original)
            category_count["records_scanned"] += 1
            if cleaned != original:
                category_count["records_changed"] += 1
                if check:
                    raise ValueError(f"Encyclopedia prose or obsolete hold remains in {path}")
                # Track changes before touching any files: failed data validation
                # leaves the original working tree intact.
                pending.append((path, cleaned))
            category_count["description_rows_removed"] += rows
            category_count["description_fields_removed"] += fields
            category_count["description_holds_cleared"] += int(holds)
        counts[category] = category_count
        for name in total:
            total[name] += category_count[name]
    if write:
        for path, cleaned in pending:
            path.write_text(
                json.dumps(cleaned, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
    return {"schema_version": 1,
            "mode": "write" if write else "check" if check else "dry_run",
            "categories": counts, "total": total}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--categories", nargs="+", required=True, choices=CATEGORIES)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = process(args.data, tuple(args.categories),
                     write=args.write, check=args.check)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
