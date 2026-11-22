#!/usr/bin/env python3
"""Read-only per-record reference/witness audit; never invent source verse links.

Reference fields are independent inherited ACAI claims. A missing general
reference is not necessarily an error, even when a key verse is present.
Exact original-word tokens can justify targeted, source-locked review only.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("explicit_instances", "pronominal_referents", "subject_referents")


def source_verses(record: dict) -> dict[str, set[str]]:
    result = {}
    for field in FIELDS:
        verses = set()
        for corpus, groups in record.get(field, {}).items():
            for group in groups:
                for word in group:
                    if isinstance(word, str) and len(word) >= 9:
                        verses.add(word[1:9])
        result[field] = verses
    return result


def audit(data: Path) -> dict:
    counters = Counter()
    kinds = defaultdict(Counter)
    samples = defaultdict(list)
    case_rows = defaultdict(list)
    for path in sorted((data / "entities").glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        sid = record["bsi"]["source_id"]
        kind = record["type"]
        references = set(record["references"])
        key_references = set(record["key_references"])
        source = source_verses(record)
        explicit = source["explicit_instances"]
        indirect = source["pronominal_referents"] | source["subject_referents"]
        base = {"source_id": sid, "type": kind,
                "path": path.relative_to(data).as_posix()}
        counters["records_scanned"] += 1
        for verse in sorted(key_references - references):
            if verse in explicit:
                category = "key_outside_general_with_exact_explicit_word"
            elif verse in indirect:
                category = "key_outside_general_with_indirect_word"
            else:
                category = "key_outside_general_without_word"
            counters[category] += 1
            kinds[category][kind] += 1
            row = {**base, "verse_id": verse}
            case_rows[category].append(row)
            if len(samples[category]) < 60:
                samples[category].append(row)
        if key_references - references:
            counters["records_key_outside_general"] += 1
        for verse in sorted(explicit - references):
            category = "explicit_word_verse_absent_general"
            counters[category] += 1
            kinds[category][kind] += 1
            row = {**base, "verse_id": verse}
            case_rows[category].append(row)
            if len(samples[category]) < 60:
                samples[category].append(row)
        if (record.get("mentioned_in_bible") is True
                and not references and not explicit):
            if not key_references:
                category = "marked_biblical_no_general_no_explicit_no_key"
            elif indirect:
                category = "marked_biblical_no_general_no_explicit_has_indirect"
            else:
                category = "marked_biblical_no_general_no_explicit_has_key"
            counters[category] += 1
            kinds[category][kind] += 1
            row = {**base, "key_references": sorted(key_references),
                   "indirect_verse_ids": sorted(indirect)}
            case_rows[category].append(row)
            if len(samples[category]) < 60:
                samples[category].append(row)
    return {
        "schema_version": 1,
        "policy": "source_claims_requires_exact_source_evidence_before_change",
        "counts": dict(sorted(counters.items())),
        "counts_by_kind": {k: dict(sorted(v.items())) for k, v in sorted(kinds.items())},
        "samples": dict(sorted(samples.items())),
        "cases": dict(sorted(case_rows.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--samples", type=int, default=25)
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()
    report = audit(args.data)
    if args.details:
        payload = report
    else:
        payload = {k: v for k, v in report.items() if k != "cases"}
        payload["samples"] = {k: v[:args.samples]
                              for k, v in payload["samples"].items()}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
