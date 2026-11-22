#!/usr/bin/env python3
"""Build a NONPUBLISHED, source-claim-only BRSI relation lookup.

This is a reversible projection of inherited exact-ID fields, NOT an
editorially approved semantic graph. No reciprocal, identity, verse or
original-word assertions are inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_existing_relation_audit", ROOT / "scripts" / "audit_entity_relationships.py")
relation_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relation_audit)

family_spec = importlib.util.spec_from_file_location(
    "brsi_existing_family_consistency_audit",
    ROOT / "scripts" / "audit_family_relation_consistency.py")
family_audit = importlib.util.module_from_spec(family_spec)
family_spec.loader.exec_module(family_audit)

# All names describe WHAT THE ORIGINAL FIELD CLAIMS, not established facts.
# Never turn partners into spouses, offspring into proven biological children,
# tribe into an ethnicity identity, or subregion_of into place equivalence.
SOURCE_PREDICATES = {
    "father": "reported_father",
    "mother": "reported_mother",
    "offspring": "reported_offspring",
    "partners": "reported_partner",
    "siblings": "reported_sibling",
    "tribe": "reported_tribe",
    "group_origin": "reported_group_origin",
    "subregion_of": "reported_subregion_of",
    "associated_places": "reported_associated_place",
    "nearby_places": "reported_nearby_place",
    "related_places": "reported_related_place",
    "tribal_area": "reported_tribal_area",
}

# The source may suggest an alias or a possible identity, but no equality
# relation follows without independent editorial and manuscript evidence.
WITHHELD_IDENTITY_FIELDS = frozenset({"possibly_same_as", "referred_to_as"})


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def build(data: Path) -> dict:
    """Index exact native references without rewriting or approving them."""
    lock = json.loads((data / "source.lock.json").read_text(encoding="utf-8"))
    audit = relation_audit.audit(data)
    unsafe = {"old_identity", "old_identity_to_quarantined",
              "current_to_quarantined", "unresolved_identity"}
    if any(audit["classifications"].get(kind, 0) for kind in unsafe):
        raise ValueError("Relation source contains stale, quarantined or unresolved links")

    # A mismatch between two inherited inverse genealogy fields is *not*
    # evidence that either field is false. Withhold both exact source claims,
    # keeping every competing ID and field path for independent review.
    family_report = family_audit.audit(data, limit=1000000)
    disagreements = family_report["conflicting_inverse_claim_examples"]
    if len(disagreements) != family_report["counts"].get(
            "different_named_parent_in_inverse_claim", 0):
        raise ValueError("Incomplete inverse-family disagreement evidence")
    disputed_fields = set()
    for row in disagreements:
        disputed_fields.add((row["claiming_parent"], "offspring", row["child"]))
        disputed_fields.add((row["child"], row["relation"],
                             row["child_named_parent"]))

    records = {}
    for path in sorted((data / "entities").glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        entity_id = record.get("id")
        if not isinstance(entity_id, str) or entity_id in records:
            raise ValueError(f"Duplicate or invalid current entity ID: {path}")
        records[entity_id] = (path.relative_to(data).as_posix(), record)

    claims = []
    seen_claim_ids = set()
    by_source, by_target = defaultdict(list), defaultdict(list)
    statuses = Counter()
    field_counts = Counter()
    withheld_fields = Counter()
    ambiguous_identity_fields = Counter()
    inverse_disagreement_fields = Counter()
    restricted_count = 0
    for source_id, (source_path, record) in sorted(records.items()):
        metadata = record.get("bsi", {})
        for link in relation_audit.walk_links(record):
            target = link["target"]
            if target.startswith("keyterm:"):
                # These excluded third-party records are not imported or
                # redistributable. Do not leak their names into a candidate.
                restricted_count += 1
                continue
            if target not in records:
                raise ValueError(f"Unresolved or quarantined relation: {source_path} {link['path']} -> {target}")
            source_field = link["path"][0] if link["path"] else None
            if not isinstance(source_field, str):
                raise ValueError(f"Missing source field: {source_path}")
            predicate = SOURCE_PREDICATES.get(source_field)
            status = ("withheld_inverse_disagreement"
                      if (source_id, source_field, target) in disputed_fields
                      else "source_unreviewed" if predicate
                      else "withheld_identity_or_alias"
                      if source_field in WITHHELD_IDENTITY_FIELDS
                      else "withheld_unclassified")
            identity = {
                "source_record_id": metadata["source_id"],
                "json_path": link["path"],
                "original_target_id": target,
            }
            claim_id = hashlib.sha256(canonical_bytes(identity)).hexdigest()
            if claim_id in seen_claim_ids:
                raise ValueError(f"Duplicate original relation witness: {source_path} {link['path']}")
            seen_claim_ids.add(claim_id)
            target_meta = records[target][1]["bsi"]
            claim = {
                "claim_id": claim_id,
                "source_id": source_id,
                "source_canonical_id": metadata["canonical_id"],
                "target_id": target,
                "target_canonical_id": target_meta["canonical_id"],
                "predicate": predicate,
                "source_field": source_field,
                "review_status": status,
                "evidence": {
                    "source_record_id": metadata["source_id"],
                    "source_record_path": source_path,
                    "source_record_sha256": metadata.get("source_sha256"),
                    "json_path": link["path"],
                    "evidence_scope": "inherited_record_field_only",
                },
            }
            claims.append(claim)
            by_source[source_id].append(claim_id)
            by_target[target].append(claim_id)
            statuses[status] += 1
            field_counts[source_field] += 1
            if status == "withheld_unclassified":
                withheld_fields[source_field] += 1
            elif status == "withheld_identity_or_alias":
                ambiguous_identity_fields[source_field] += 1
            elif status == "withheld_inverse_disagreement":
                inverse_disagreement_fields[source_field] += 1

    if len(claims) + restricted_count != audit["structured_relationships"]:
        raise ValueError("A source relation disappeared during projection")
    return {
        "format": "brsi-entity-source-relation-candidates",
        "schema_version": 1,
        "publication_approved": False,
        "source": {
            "source_repository": lock["source_repository"],
            "source_commit": lock["source_commit"],
            "source_snapshot_sha256": lock["source_snapshot_sha256"],
            "source_license": lock["source_license"],
        },
        "counts": {
            "source_relationships": audit["structured_relationships"],
            "indexed_claims": len(claims),
            "excluded_restricted_keyterm_claims": restricted_count,
            "source_unreviewed": statuses["source_unreviewed"],
            "withheld_unclassified": statuses["withheld_unclassified"],
            "withheld_identity_or_alias": statuses["withheld_identity_or_alias"],
            "withheld_inverse_disagreement": statuses["withheld_inverse_disagreement"],
            "inverse_disagreement_cases": len(disagreements),
            "by_source_field": dict(sorted(field_counts.items())),
            "unclassified_by_field": dict(sorted(withheld_fields.items())),
            "withheld_identity_or_alias_by_field": dict(sorted(ambiguous_identity_fields.items())),
            "withheld_inverse_disagreement_by_field": dict(sorted(inverse_disagreement_fields.items())),
        },
        "claims": claims,
        "by_source": dict(sorted(by_source.items())),
        "by_target": dict(sorted(by_target.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.data.resolve()):
        parser.error("Cannot overwrite canonical source data")
    result = build(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result) + b"\n")
    print(json.dumps(result["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
