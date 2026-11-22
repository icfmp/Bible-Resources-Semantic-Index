#!/usr/bin/env python3
"""One-time, lossless BSI native entity materialization from the frozen ACAI baseline.

Only generated output directories are modified. Original ACAI bytes are never edited.
Do not publish generated keyterms without separate source-field rights clearance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("legacy_bsi_builder", ROOT / "scripts" / "compile_index.py")
LEGACY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEGACY)
CATEGORIES = LEGACY.CATEGORIES
LINK_FIELDS = LEGACY.LINK_FIELDS


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def materialize(source: Path, output: Path, *, lock: dict, editorial: dict,
                absences: dict, verse_absences: dict, qualifications: dict,
                include_restricted: bool = False) -> dict:
    """Apply ALL reviewed decisions once, retaining the full unmodified source fields.

    The resulting version-controlled records become the editable BSI source of truth;
    historical source fingerprints and editorial evidence remain attached.
    """
    old = LEGACY.build(source, lock, editorial, absences, verse_absences, qualifications)
    by_source = {record["source_id"]: record for record in old["entities"]}
    quarantined = {record["source_id"]: record for record in old["quarantined"]}
    total = Counter()
    written = []
    pending_rights = []
    source_ids = set()
    for category, prefix in CATEGORIES.items():
        folder = source / category / "json"
        for src in sorted(folder.glob("*.json")):
            raw = src.read_bytes()
            original = json.loads(raw)
            sid = original["id"]
            if sid in source_ids:
                raise ValueError(f"Duplicate source identity: {sid}")
            source_ids.add(sid)
            total[category] += 1
            if sid.startswith("keyterm:") and not include_restricted:
                pending_rights.append(sid)
                continue
            if sid in quarantined:
                # Quarantined source material is retained, not reintroduced as a
                # reader-facing identity or silently dropped.
                rec = copy.deepcopy(original)
                rec["bsi"] = {
                    "source_id": sid,
                    "source_sha256": hashlib.sha256(raw).hexdigest(),
                    "state": "quarantined",
                    "reason": quarantined[sid]["reason"],
                    "evidence": quarantined[sid]["evidence"],
                }
                target = output / "quarantined" / category / src.name
            else:
                corrected = by_source.get(sid)
                if corrected is None:
                    raise ValueError(f"Missing derived BSI entity for {sid}")
                rec = copy.deepcopy(original)
                # All untouched ACAI fields, including labels, relationships and
                # non-indexing data, are retained exactly as structured values.
                rec["id"] = corrected["id"]
                rec["primary_id"] = corrected["canonical_id"]
                rec["type"] = corrected["kind"]
                rec["references"] = copy.deepcopy(corrected["references"])
                rec["key_references"] = copy.deepcopy(corrected["key_references"])
                for field in LINK_FIELDS:
                    rec[field] = copy.deepcopy(corrected["occurrences"][field])
                rec["bsi"] = {
                    "source_id": sid,
                    "source_primary_id": corrected["source_primary_id"],
                    "source_sha256": corrected["source_sha256"],
                    "review_status": corrected["review_status"],
                    "canonical_id": corrected["canonical_id"],
                }
                if "editorial_reason" in corrected:
                    rec["bsi"]["editorial_reason"] = corrected["editorial_reason"]
                    rec["bsi"]["editorial_evidence"] = copy.deepcopy(corrected["editorial_evidence"])
                target = output / "entities" / category / src.name
                # Strict equality to the already validated historical derived
                # representation; no semantic editorial decision is introduced.
                assert rec["id"] == corrected["id"]
                assert rec["primary_id"] == corrected["canonical_id"]
                assert rec["references"] == corrected["references"]
                assert all(rec[field] == corrected["occurrences"][field] for field in LINK_FIELDS)
            if target.exists():
                raise ValueError(f"Refusing to overwrite an existing BSI record: {target}")
            save(target, rec)
            written.append(target.relative_to(output).as_posix())

    if len(source_ids) != lock["source_records_expected"]:
        raise ValueError("Incomplete ACAI input records")
    if len(source_ids) != len(by_source) + len(quarantined):
        raise ValueError("Legacy indexed and quarantined records do not cover ACAI")
    if len(pending_rights) != (total["keyterms"] if not include_restricted else 0):
        raise ValueError("Source-rights review gate did not cover all keyterms")
    report = {
        "schema_version": 1,
        "state": "review_candidate_not_publication_authorization",
        "source_repository": lock["source_repository"],
        "source_commit": lock["source_commit"],
        "source_snapshot_sha256": old["provenance"]["source_snapshot_sha256"],
        "source_records": len(source_ids),
        "category_counts": dict(sorted(total.items())),
        "active_legacy_entities": len(by_source),
        "quarantined_legacy": len(quarantined),
        "written_records": len(written),
        "restricted_unpublished_keyterms": len(pending_rights),
        "restricted_source_ids": pending_rights,
        "written_paths": written,
        "legacy_statistics": old["statistics"],
    }
    save(output / "migration-manifest.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Exact pinned ACAI checkout")
    parser.add_argument("--output", type=Path, required=True, help="Must be a new, empty directory")
    parser.add_argument("--include-restricted-for-local-review", action="store_true",
                        help="LOCAL REVIEW ONLY. Never commit keyterms without rights clearance")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output directory must not exist or must be empty")
    if args.output.resolve() == args.source.resolve():
        parser.error("Output must not be the original ACAI checkout")
    lock = load(ROOT / "data/source.lock.json")
    materialize(
        args.source, args.output,
        lock=lock, editorial=load(ROOT / "data/editorial-decisions.json"),
        absences=load(ROOT / "data/source-unattested-words.json"),
        verse_absences=load(ROOT / "data/source-unattested-verses.json"),
        qualifications=load(ROOT / "data/source-reference-qualifications.json"),
        include_restricted=args.include_restricted_for_local_review,
    )
    print((args.output / "migration-manifest.json").read_text(encoding="utf-8")[:1600])


if __name__ == "__main__":
    main()
