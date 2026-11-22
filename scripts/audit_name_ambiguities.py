#!/usr/bin/env python3
"""Read-only audit of potentially ambiguous BRSI names; never guess identities.

Source working labels are not reviewed. Candidate groups are based on a
conservative display-name prefix, not on lexical or historical equivalence.
Only canonical identity IDs and exact existing source references support review.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAREN_QUALIFIER = re.compile(r"\\s+\\([^()]*\\)$")


def base_name(name: str) -> str:
    value = unicodedata.normalize("NFKC", name).strip()
    if not value:
        raise ValueError("Empty source name")
    # Display qualifiers are NOT reviewed identities. Only strip one simple
    # final parenthetical qualifier; never normalize distinct original lemmas.
    return PAREN_QUALIFIER.sub("", value).strip().casefold()


def audit(data: Path, *, sample_limit: int = 15) -> dict:
    if sample_limit < 0:
        raise ValueError("sample_limit must not be negative")
    groups = defaultdict(list)
    count = 0
    for path in sorted((data / "entities").glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        bsi = record["bsi"]
        label = record.get("localizations", {}).get("eng", {}).get("preferred_label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Missing English source label: {path}")
        count += 1
        groups[(record["type"], base_name(label))].append({
            "id": record["id"],
            "canonical_id": bsi["canonical_id"],
            "source_id": bsi["source_id"],
            "has_reviewed_hint": bsi.get("identity_hint", {}).get("review_status") == "editorially_reviewed",
            "key_reference_count": len(record["key_references"]),
        })
    candidates = []
    for (kind, normalized), records in groups.items():
        identities = {r["canonical_id"] for r in records}
        if len(identities) <= 1:
            continue
        candidates.append({
            "kind": kind,
            "normalized_source_name": normalized,
            "candidate_record_count": len(records),
            "distinct_canonical_id_count": len(identities),
            "without_reviewed_hint": sum(not r["has_reviewed_hint"] for r in records),
            "records": sorted(records, key=lambda row: (row["source_id"], row["id"])),
        })
    candidates.sort(key=lambda g: (-g["distinct_canonical_id_count"],
                                    -g["candidate_record_count"],
                                    g["kind"], g["normalized_source_name"]))
    return {
        "schema_version": 1,
        "status": "review_candidates_only_no_identity_assertions",
        "source_records_scanned": count,
        "ambiguous_display_name_groups": len(candidates),
        "records_in_groups": sum(g["candidate_record_count"] for g in candidates),
        "records_without_reviewed_hint": sum(g["without_reviewed_hint"] for g in candidates),
        "sample_groups": candidates[:sample_limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--sample-limit", type=int, default=15)
    args = parser.parse_args()
    print(json.dumps(audit(args.data, sample_limit=args.sample_limit),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
