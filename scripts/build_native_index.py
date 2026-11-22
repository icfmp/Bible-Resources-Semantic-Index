#!/usr/bin/env python3
"""Build the BSI entity index from VERSIONED CURRENT native BSI records.

No ACAI fetch, original-source replay, or editorial patch application is used.
The old historical builder remains only as an independent migration test.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# New BSI-owned records may be added without inventing a matching ACAI source.
# Work is already a reviewed canonical identity kind in the native entity index.
NATIVE_CATEGORIES = {"works": "work"}
spec = importlib.util.spec_from_file_location("bsi_link_finalizer", ROOT / "scripts" / "compile_index.py")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

policy_spec = importlib.util.spec_from_file_location(
    "brsi_localization_policy", ROOT / "scripts" / "localization_policy.py")
localization_policy = importlib.util.module_from_spec(policy_spec)
policy_spec.loader.exec_module(localization_policy)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build(data: Path = ROOT / "data") -> dict:
    lock = read(data / "source.lock.json")
    manifest = read(data / "migration" / "acai-baseline-materialization.json")
    if manifest["source_commit"] != lock["source_commit"]:
        raise ValueError("Native baseline source commit does not match immutable provenance")
    if manifest["source_snapshot_sha256"] != lock["source_snapshot_sha256"]:
        raise ValueError("Native baseline source digest mismatch")
    entries, quarantined, seen_source = [], [], set()
    imported_source_ids = set()
    native_source_ids = set()
    for category in (*legacy.CATEGORIES, *NATIVE_CATEGORIES):
        expected_prefix = legacy.CATEGORIES.get(category, NATIVE_CATEGORIES.get(category))
        directory = data / "entities" / category
        for path in sorted(directory.glob("*.json")):
            record = read(path)
            # Reject malformed/unknown editorial holds rather than letting a
            # future reader-facing exporter silently treat them as approved.
            localization_policy.validated_holds(record)
            metadata = record.get("bsi", {})
            sid = metadata.get("source_id")
            if not isinstance(sid, str) or sid in seen_source:
                raise ValueError(f"Missing or duplicate native source ID in {path}")
            seen_source.add(sid)
            if category == "keyterms":
                raise ValueError("Restricted keyterm record unexpectedly in approved native data")
            origin = metadata.get("origin")
            if origin == "bsi":
                if sid != f"bsi:{expected_prefix}:{path.stem}":
                    raise ValueError(f"Incorrect BSI-native identity provenance: {path}: {sid}")
                if not isinstance(metadata.get("editorial_reason"), str) or not metadata["editorial_reason"].strip():
                    raise ValueError(f"BSI-native record lacks editorial reason: {path}")
                evidence = metadata.get("editorial_evidence")
                if not isinstance(evidence, list) or not evidence or any(
                        not isinstance(item, str) or not item.strip() for item in evidence):
                    raise ValueError(f"BSI-native record lacks source evidence: {path}")
                if metadata.get("review_status") != "editorially_reviewed":
                    raise ValueError(f"BSI-native record must be reviewed: {path}")
                native_source_ids.add(sid)
            elif origin in (None, "acai"):
                if category in NATIVE_CATEGORIES:
                    raise ValueError(f"New BSI category cannot masquerade as ACAI: {path}")
                if sid != f"{expected_prefix}:{path.stem}":
                    raise ValueError(f"Historical source path/ID mismatch: {path}: {sid}")
                if not isinstance(metadata.get("source_sha256"), str) or len(metadata["source_sha256"]) != 64:
                    raise ValueError(f"Imported record lacks source SHA-256: {path}")
                imported_source_ids.add(sid)
            else:
                raise ValueError(f"Unsupported entity provenance origin: {path}: {origin}")
            entry = {
                "id": record["id"], "kind": record["type"],
                "canonical_id": metadata["canonical_id"],
                "source_id": sid,
                "source_primary_id": metadata["source_primary_id"],
                "source_sha256": metadata.get("source_sha256"),
                "review_status": metadata["review_status"],
                "references": copy.deepcopy(record["references"]),
                "key_references": copy.deepcopy(record["key_references"]),
                "occurrences": {
                    field: copy.deepcopy(record.get(field, {}))
                    for field in legacy.LINK_FIELDS
                },
            }
            for field in ("editorial_evidence", "editorial_reason"):
                if field in metadata:
                    entry[field] = copy.deepcopy(metadata[field])
            if not isinstance(entry["id"], str) or not isinstance(entry["canonical_id"], str):
                raise ValueError("Missing canonical identity in " + str(path))
            entries.append(entry)
        directory = data / "quarantined" / category
        for path in sorted(directory.glob("*.json")):
            record = read(path)
            metadata = record["bsi"]
            if metadata.get("state") != "quarantined":
                raise ValueError("Quarantined record missing explicit state")
            sid = metadata["source_id"]
            if sid in seen_source:
                raise ValueError("Quarantine duplicates a source identity: " + sid)
            seen_source.add(sid)
            if metadata.get("origin") == "bsi":
                if not sid.startswith("bsi:" + expected_prefix + ":"):
                    raise ValueError(f"Incorrect BSI quarantine source ID: {path}")
                native_source_ids.add(sid)
            elif metadata.get("origin") in (None, "acai"):
                if sid != f"{expected_prefix}:{path.stem}":
                    raise ValueError(f"Historical quarantined source ID mismatch: {path}")
                imported_source_ids.add(sid)
            else:
                raise ValueError(f"Unsupported quarantine provenance: {path}")
            quarantined.append({
                "source_id": sid, "source_sha256": metadata.get("source_sha256"),
                "reason": metadata["reason"], "evidence": metadata["evidence"],
            })
    if manifest["written_records"] + manifest["restricted_unpublished_keyterms"] != manifest["source_records"]:
        raise ValueError("Historical source completeness accounting invalid")
    # The migration manifest is an immutable inventory, not a ceiling on
    # evolving BSI data. The original source IDs must never disappear, but
    # independently evidenced new BSI entries are permitted.
    baseline_sources = set()
    for migrated_path in manifest["written_paths"]:
        section, category, filename = Path(migrated_path).parts
        if section not in ("entities", "quarantined") or category not in legacy.CATEGORIES:
            raise ValueError(f"Unexpected historical migration path: {migrated_path}")
        basename = Path(filename).stem
        baseline_sources.add(f"{legacy.CATEGORIES[category]}:{basename}")
    if len(baseline_sources) != manifest["written_records"]:
        raise ValueError("Historical source manifest has duplicate identities")
    if imported_source_ids != baseline_sources:
        missing = sorted(baseline_sources - imported_source_ids)
        unexpected = sorted(imported_source_ids - baseline_sources)
        raise ValueError(f"Imported ACAI entity identities changed: missing={missing[:5]}, unexpected={unexpected[:5]}")
    if len(seen_source) != len(imported_source_ids) + len(native_source_ids):
        raise ValueError("Native source identity collision")
    words = set()
    references = set()
    for entry in entries:
        references.update(entry["references"])
        for field in legacy.LINK_FIELDS:
            for corpus, groups in entry["occurrences"][field].items():
                edition = legacy.canonical_source_corpus(lock, corpus)
                words.update(f"{edition}:{word}" for group in groups for word in group)
    absence = copy.deepcopy(read(data / "source-unattested-words.json"))
    absence["word_ids"] = [
        w for w in absence["word_ids"] if f"{absence['corpus']}:{w}" in words
    ]
    verse_absence = copy.deepcopy(read(data / "source-unattested-verses.json"))
    verse_absence["verse_ids"] = [
        verse for verse in verse_absence["verse_ids"] if verse in references
    ]
    if "verse_qualifications" in verse_absence:
        relevant = set(verse_absence["verse_ids"])
        verse_absence["verse_qualifications"] = [
            row for row in verse_absence["verse_qualifications"]
            if row["verse_id"] in relevant
        ]
    qualifications = copy.deepcopy(read(data / "source-reference-qualifications.json"))
    qualifications["claims"] = [
        row for row in qualifications["claims"]
        if row["source_id"] in seen_source
    ]
    result = legacy.finalize_index(
        entries, quarantined, lock, absence, verse_absence, qualifications,
        manifest["source_snapshot_sha256"], manifest["source_records"],
    )
    result["distribution_profile"] = {
        "name": "bsi-v0.1-without-keyterms",
        "excluded_kinds": ["keyterm"],
        "excluded_entity_count": manifest["restricted_unpublished_keyterms"],
        "source_records_unchanged": True,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.data.resolve()):
        parser.error("Output must not overwrite versioned native data")
    result = build(args.data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(result["statistics"], sort_keys=True))


if __name__ == "__main__":
    main()
