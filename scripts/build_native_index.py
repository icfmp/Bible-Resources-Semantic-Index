#!/usr/bin/env python3
"""Build the BSI entity index from VERSIONED CURRENT native BSI records.

No ACAI fetch, original-source replay, or editorial patch application is used.
Shared identity/link finalization comes from the maintained entity_index_core.py;
no historical ACAI rebuild code is imported.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# New BSI-owned records may be added without inventing a matching ACAI source.
# Work is already a reviewed canonical identity kind in the native entity index.
NATIVE_CATEGORIES = {"works": "work"}
spec = importlib.util.spec_from_file_location("brsi_entity_index_core", ROOT / "scripts" / "entity_index_core.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

policy_spec = importlib.util.spec_from_file_location(
    "brsi_localization_policy", ROOT / "scripts" / "localization_policy.py")
localization_policy = importlib.util.module_from_spec(policy_spec)
policy_spec.loader.exec_module(localization_policy)

identity_spec = importlib.util.spec_from_file_location(
    "brsi_identity_policy", ROOT / "scripts" / "identity_policy.py")
identity_policy = importlib.util.module_from_spec(identity_spec)
identity_spec.loader.exec_module(identity_policy)


reference_spec = importlib.util.spec_from_file_location(
    "brsi_reference_policy", ROOT / "scripts" / "reference_policy.py")
reference_policy = importlib.util.module_from_spec(reference_spec)
reference_spec.loader.exec_module(reference_policy)

offspring_spec = importlib.util.spec_from_file_location(
    "brsi_offspring_target_policy", ROOT / "scripts" / "offspring_target_policy.py")
offspring_policy = importlib.util.module_from_spec(offspring_spec)
offspring_spec.loader.exec_module(offspring_policy)


SOURCE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _unique_json_keys(pairs):
    """Never let JSON silently replace an earlier source field."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _reject_non_json_number(token):
    raise ValueError(f"Nonstandard JSON number {token!r}")


def read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_json_keys,
                          parse_constant=_reject_non_json_number)
    except (ValueError, UnicodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc


def validate_source_sha256(value, path: Path) -> None:
    if not isinstance(value, str) or SOURCE_SHA256.fullmatch(value) is None:
        raise ValueError(f"Invalid imported source SHA-256 at {path}")


def validate_entity_file_layout(data: Path) -> None:
    """Reject unrecognized or nested JSON silently excluded by glob('*.json')."""
    known = set(core.CATEGORIES) | set(NATIVE_CATEGORIES)
    for state in ("entities", "quarantined"):
        root = data / state
        if not root.is_dir():
            raise ValueError(f"Missing native entity directory: {root}")
        for category in root.iterdir():
            if category.is_symlink():
                raise ValueError(f"Native entity symlinks are not permitted: {category}")
            if category.is_dir() and category.name not in known:
                raise ValueError(f"Unsupported native entity category: {category}")
        # Check all case variants of JSON filenames: glob('*.json') would
        # silently ignore *.JSON and mixed-case files on case-sensitive hosts.
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"Native entity symlinks are not permitted: {path}")
            if not path.is_file() or path.suffix.lower() != ".json":
                continue
            relative = path.relative_to(root)
            if (len(relative.parts) != 2 or relative.parts[0] not in known
                    or path.suffix != ".json"):
                raise ValueError(f"Unindexed or nested native entity JSON: {path}")


def build(data: Path = ROOT / "data") -> dict:
    lock = read(data / "source.lock.json")
    manifest = read(data / "migration" / "acai-baseline-materialization.json")
    if manifest["source_commit"] != lock["source_commit"]:
        raise ValueError("Native baseline source commit does not match immutable provenance")
    if manifest["source_snapshot_sha256"] != lock["source_snapshot_sha256"]:
        raise ValueError("Native baseline source digest mismatch")
    validate_entity_file_layout(data)
    entries, quarantined, seen_source = [], [], set()
    imported_source_ids = set()
    native_source_ids = set()
    for category in (*core.CATEGORIES, *NATIVE_CATEGORIES):
        expected_prefix = core.CATEGORIES.get(category, NATIVE_CATEGORIES.get(category))
        directory = data / "entities" / category
        for path in sorted(directory.glob("*.json")):
            record = read(path)
            # BRSI indexes identities and source links, never biographies.
            # Prevent an old ACAI import from silently restoring prose even
            # when a caller invokes this builder without running CI.
            localized = record.get("localizations", {})
            if not isinstance(localized, dict) or any(
                not isinstance(fields, dict) or "descriptions" in fields
                for fields in localized.values()
            ):
                raise ValueError(f"Encyclopedia descriptions forbidden in current BRSI record: {path}")
            # An identity index must not retain inherited encyclopedia prose,
            # even if a caller runs the native builder without the offline CI.
            if "descriptions" in record:
                raise ValueError(f"Encyclopedia descriptions forbidden in current BRSI record: {path}")
            # Only the working English identity label belongs to this index.
            # Other language display names stay recoverable from pinned ACAI.
            if any(language != "eng" for language in localized):
                raise ValueError(f"Redundant translated label not permitted in BRSI: {path}")
            # Reject obsolete prose holds and foreign-language selectors as
            # well as malformed/unknown holds; legacy import pruners no longer
            # run as part of the maintained build.
            withheld = localization_policy.validated_holds(record)
            if "descriptions" in withheld:
                raise ValueError(f"Obsolete inherited encyclopedia prose hold in {path}")
            if any("." in selector and not selector.startswith("eng.") for selector in withheld):
                raise ValueError(f"Redundant translated localization hold in {path}")
            identity_policy.validate_identity_hint(record)
            reference_policy.validate_reference_fields(record)
            offspring_policy.validate_offspring_targets(record)
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
                if metadata.get("source_sha256") is not None:
                    raise ValueError(f"BSI-native entity must not claim an ACAI source SHA-256: {path}")
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
                english = localized.get("eng")
                if (not isinstance(english, dict)
                        or not isinstance(english.get("preferred_label"), str)
                        or not english["preferred_label"].strip()):
                    raise ValueError(f"Imported entity lacks English working identity label: {path}")
                if category in NATIVE_CATEGORIES:
                    raise ValueError(f"New BSI category cannot masquerade as ACAI: {path}")
                if sid != f"{expected_prefix}:{path.stem}":
                    raise ValueError(f"Historical source path/ID mismatch: {path}: {sid}")
                validate_source_sha256(metadata.get("source_sha256"), path)
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
                    for field in core.LINK_FIELDS
                },
            }
            for field in ("editorial_evidence", "editorial_reason"):
                if field in metadata:
                    entry[field] = copy.deepcopy(metadata[field])
            # Source category may differ from a reviewed reclassification
            # (e.g. inherited people/Dinaite.json -> group:Dinaite), but
            # public kind must match the current canonical typed identity.
            kind_prefix = {"literary_work": "work"}.get(entry["kind"], entry["kind"])
            if (not isinstance(entry["id"], str)
                    or not entry["id"].startswith(f"{kind_prefix}:")
                    or not entry["id"].split(":", 1)[1]
                    or not isinstance(entry["canonical_id"], str)
                    or not entry["canonical_id"].startswith(f"{kind_prefix}:")
                    or not entry["canonical_id"].split(":", 1)[1]):
                raise ValueError(f"Invalid typed canonical entity identity in {path}")
            if origin == "bsi" and (entry["id"] != f"{expected_prefix}:{path.stem}"
                    or entry["canonical_id"] != entry["id"]
                    or record.get("primary_id") != entry["id"]
                    or record.get("type") != "literary_work"):
                raise ValueError(f"Incorrect BSI-native identity type or owner: {path}")
            entries.append(entry)
        directory = data / "quarantined" / category
        for path in sorted(directory.glob("*.json")):
            if category == "keyterms":
                raise ValueError("Restricted keyterm record unexpectedly in public native quarantine")
            record = read(path)
            metadata = record["bsi"]
            if metadata.get("state") != "quarantined":
                raise ValueError("Quarantined record missing explicit state")
            sid = metadata["source_id"]
            if sid in seen_source:
                raise ValueError("Quarantine duplicates a source identity: " + sid)
            seen_source.add(sid)
            if not isinstance(metadata.get("reason"), str) or not metadata["reason"].strip():
                raise ValueError(f"Quarantine needs a documented reason: {path}")
            proof = metadata.get("evidence")
            if (not isinstance(proof, list) or not proof
                    or any(not isinstance(item, str) or not item.strip() for item in proof)):
                raise ValueError(f"Quarantine needs source evidence: {path}")
            if metadata.get("origin") == "bsi":
                if not sid.startswith("bsi:" + expected_prefix + ":"):
                    raise ValueError(f"Incorrect BSI quarantine source ID: {path}")
                if metadata.get("source_sha256") is not None:
                    raise ValueError(f"BSI-native quarantine must not claim ACAI source SHA-256: {path}")
                native_source_ids.add(sid)
            elif metadata.get("origin") in (None, "acai"):
                if sid != f"{expected_prefix}:{path.stem}":
                    raise ValueError(f"Historical quarantined source ID mismatch: {path}")
                validate_source_sha256(metadata.get("source_sha256"), path)
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
        if section not in ("entities", "quarantined") or category not in core.CATEGORIES:
            raise ValueError(f"Unexpected historical migration path: {migrated_path}")
        basename = Path(filename).stem
        baseline_sources.add(f"{core.CATEGORIES[category]}:{basename}")
    if len(baseline_sources) != manifest["written_records"]:
        raise ValueError("Historical source manifest has duplicate identities")
    if imported_source_ids != baseline_sources:
        missing = sorted(baseline_sources - imported_source_ids)
        unexpected = sorted(imported_source_ids - baseline_sources)
        raise ValueError(f"Imported ACAI entity identities changed: missing={missing[:5]}, unexpected={unexpected[:5]}")
    if len(seen_source) != len(imported_source_ids) + len(native_source_ids):
        raise ValueError("Native source identity collision")
    current_ids = {entry["id"] for entry in entries}
    for entry in entries:
        if entry["canonical_id"] not in current_ids:
            raise ValueError(
                f"Canonical target missing from current index: "
                f"{entry['source_id']} -> {entry['canonical_id']}")
    words = set()
    references = set()
    for entry in entries:
        references.update(entry["references"])
        for field in core.LINK_FIELDS:
            for corpus, groups in entry["occurrences"][field].items():
                edition = core.canonical_source_corpus(lock, corpus)
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
    result = core.finalize_index(
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
