#!/usr/bin/env python3
"""Read-only family-link cross-check for current BRSI person records.

Two inverse source claims can disagree without proving either is false.
Aliases must be compared by reviewed canonical ID; no entity is merged,
rewritten, filtered or given new fictional relatives by this audit.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(data: Path, *, limit: int = 30) -> dict:
    if limit < 0:
        raise ValueError("Negative report limit")
    people = {}
    for path in sorted((data / "entities" / "people").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        identity = record.get("id")
        if not isinstance(identity, str) or identity in people:
            raise ValueError(f"Missing or duplicate current person identity: {path}")
        people[identity] = record
    canonical = {id_: doc["bsi"]["canonical_id"] for id_, doc in people.items()}
    # These are CURRENT identities, including any reviewed reclassifications
    # in other folders. A person->group child pointer is a valid target ID
    # structurally, but it is not a person-to-person genealogy.
    nonperson_targets = {}
    for path in sorted((data / "entities").glob("*/*.json")):
        if path.parent.name == "people":
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        nonperson_targets[record["id"]] = record["type"]
    stats = Counter()
    conflicts = []
    nonperson_examples = []
    for identity, person in sorted(people.items()):
        gender = person.get("gender")
        role = {"male": "father", "female": "mother"}.get(gender)
        for child_id in person.get("offspring", []):
            stats["offspring_claims"] += 1
            child = people.get(child_id)
            if child is None:
                # Missing references have their own exhaustive exact-ID audit;
                # *here* classify valid source pointers to another kind.
                kind = nonperson_targets.get(child_id)
                if kind:
                    stats["offspring_target_outside_people_folder"] += 1
                else:
                    stats["offspring_target_not_found_in_current_entity_data"] += 1
                nonperson_examples.append({
                    "claiming_parent": identity,
                    "child_target": child_id,
                    "target_kind_if_known": kind,
                })
                continue
            if role is None:
                stats["parent_role_unknown"] += 1
                continue
            direct = child.get(role)
            if not isinstance(direct, str) or not direct:
                stats["child_missing_matching_parent_role"] += 1
                continue
            if canonical.get(direct, direct) == canonical[identity]:
                stats["inverse_claims_agree_canonically"] += 1
                continue
            stats["different_named_parent_in_inverse_claim"] += 1
            conflicts.append({
                "claiming_parent": identity,
                "claiming_parent_canonical_id": canonical[identity],
                "child": child_id,
                "relation": role,
                "child_named_parent": direct,
                "child_named_parent_canonical_id": canonical.get(direct, direct),
            })
    conflicts.sort(key=lambda x: (x["child"], x["relation"], x["claiming_parent"]))
    return {
        "schema_version": 1,
        "policy": "source_inherited_inverse_claim_candidate_review_only",
        "person_records_scanned": len(people),
        "counts": dict(sorted(stats.items())),
        "conflicting_inverse_claim_examples": conflicts[:limit],
        "offspring_outside_person_folder_examples": sorted(
            nonperson_examples,
            key=lambda x: (x["claiming_parent"], x["child_target"])
        )[:limit],
        "warning": (
            "A mismatch is a review candidate, not proof of a fabricated person "
            "or authority to delete genealogy. Parent roles may be incomplete, "
            "one-sided, variant or editorially disputed."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(audit(args.data, limit=args.limit),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
