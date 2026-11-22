#!/usr/bin/env python3
"""Read-only BRSI identity/alias inventory; aggregate counts only, no prose."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POTENTIAL_REVIEW_FIELDS = ("speeches", "roles", "geocoordinates",
                           "alternate_sources", "non_biblical",
                           "only_mentioned_in_apocrypha", "lemmas")


def audit(data: Path) -> dict:
    kinds = Counter()
    source_status = Counter()
    labels = Counter()
    aliases = Counter()
    other_fields = Counter()
    description_fields = 0
    reviewed_hints = 0
    missing_working_label = 0
    files = sorted((data / "entities").glob("*/*.json"))
    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        kinds[record.get("type", "<missing>")] += 1
        bsi = record.get("bsi", {})
        source_status[bsi.get("review_status", "<missing>")] += 1
        reviewed_hints += int("identity_hint" in bsi)
        for field in POTENTIAL_REVIEW_FIELDS:
            if field in record and record[field] not in (None, [], {}, False, ""):
                other_fields[field] += 1
        locs = record.get("localizations", {})
        if "eng" not in locs or not locs["eng"].get("preferred_label"):
            missing_working_label += 1
        for lang, fields in locs.items():
            if "descriptions" in fields:
                description_fields += 1
            if fields.get("preferred_label"):
                labels[lang] += 1
            if fields.get("alternate_labels"):
                aliases[lang] += 1
    return {
        "schema_version": 1,
        "policy": "aggregate_source_identity_inventory_only",
        "records": len(files),
        "types": dict(sorted(kinds.items())),
        "review_status": dict(sorted(source_status.items())),
        "reviewed_identity_hints": reviewed_hints,
        "missing_english_source_label": missing_working_label,
        "description_fields_remaining": description_fields,
        "source_labels_by_language": dict(sorted(labels.items())),
        "source_alias_sets_by_language": dict(sorted(aliases.items())),
        "non_label_source_field_presence": dict(sorted(other_fields.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    print(json.dumps(audit(args.data), sort_keys=True))


if __name__ == "__main__":
    main()
