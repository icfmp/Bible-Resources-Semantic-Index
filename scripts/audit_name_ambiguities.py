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
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAREN_QUALIFIER = re.compile(r"\s+\([^()]*\)$")


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
            "_key_references": set(record["key_references"]),
            "_explicit_words": {
                (corpus.lower(), word)
                for corpus, grouped in record.get("explicit_instances", {}).items()
                for group in grouped for word in group
            },
        })
    candidates = []
    unresolved_samples = []
    for (kind, normalized), records in groups.items():
        identities = {r["canonical_id"] for r in records}
        if len(identities) <= 1:
            continue
        # Collapse multiple source aliases to one canonical owner before
        # checking whether an anchor is distinguishing within this group.
        by_canonical = defaultdict(lambda: {"verses": set(), "words": set()})
        for row in records:
            owner = by_canonical[row["canonical_id"]]
            owner["verses"].update(row["_key_references"])
            owner["words"].update(row["_explicit_words"])
        verse_owners = defaultdict(set)
        word_owners = defaultdict(set)
        for canonical_id, owner in by_canonical.items():
            for verse in owner["verses"]:
                verse_owners[verse].add(canonical_id)
            for word in owner["words"]:
                word_owners[word].add(canonical_id)
        result_records = []
        for row in records:
            owner = by_canonical[row["canonical_id"]]
            if any(len(verse_owners[v]) == 1 for v in owner["verses"]):
                evidence_class = "distinct_source_key_verse_for_triage"
            elif any(len(word_owners[w]) == 1 for w in owner["words"]):
                evidence_class = "distinct_original_word_for_triage"
            else:
                evidence_class = "not_distinguished_by_key_verses_or_explicit_words"
            if (evidence_class == "not_distinguished_by_key_verses_or_explicit_words"
                    and not row["has_reviewed_hint"]):
                unresolved_samples.append({
                    "kind": kind,
                    "normalized_source_name": normalized,
                    "source_id": row["source_id"],
                    "canonical_id": row["canonical_id"],
                    "key_references": sorted(row["_key_references"]),
                    "explicit_word_ids": [
                        f"{corpus}:{word}"
                        for corpus, word in sorted(row["_explicit_words"])
                    ][:16],
                })
            result_records.append({
                k: v for k, v in row.items() if not k.startswith("_")
            } | {"triage_evidence_class": evidence_class})
        candidates.append({
            "kind": kind,
            "normalized_source_name": normalized,
            "candidate_record_count": len(records),
            "distinct_canonical_id_count": len(identities),
            "without_reviewed_hint": sum(not r["has_reviewed_hint"] for r in records),
            "records": sorted(result_records,
                              key=lambda row: (row["source_id"], row["id"])),
        })
    candidates.sort(key=lambda g: (-g["distinct_canonical_id_count"],
                                    -g["candidate_record_count"],
                                    g["kind"], g["normalized_source_name"]))
    triage = Counter(
        record["triage_evidence_class"]
        for group in candidates for record in group["records"]
    )
    unresolved_without_hint = sum(
        record["triage_evidence_class"] == "not_distinguished_by_key_verses_or_explicit_words"
        and not record["has_reviewed_hint"]
        for group in candidates for record in group["records"]
    )
    return {
        "schema_version": 1,
        "status": "review_candidates_only_no_identity_assertions",
        "source_records_scanned": count,
        "ambiguous_display_name_groups": len(candidates),
        "records_in_groups": sum(g["candidate_record_count"] for g in candidates),
        "records_without_reviewed_hint": sum(g["without_reviewed_hint"] for g in candidates),
        "source_evidence_triage": dict(sorted(triage.items())),
        "unresolved_without_reviewed_hint": unresolved_without_hint,
        "unresolved_source_examples": sorted(
            unresolved_samples,
            key=lambda row: (row["kind"], row["normalized_source_name"],
                             row["source_id"]),
        )[:20],
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
