#!/usr/bin/env python3
"""Historical ACAI-source entity compiler, retained for regression tests only.

ACAI is a pinned data witness, not the authority for our published identities.
Neither biblical source words nor original source files are ever edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

# Preserve the verified historical builder contract while extracting the
# finalization policy shared with the canonical BRSI-native process.
import importlib.util

_core_spec = importlib.util.spec_from_file_location(
    "brsi_entity_index_core", Path(__file__).resolve().parents[2] / "scripts" / "entity_index_core.py")
core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(core)
CATEGORIES = core.CATEGORIES
LINK_FIELDS = core.LINK_FIELDS
canonical_source_corpus = core.canonical_source_corpus
finalize_index = core.finalize_index


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def checked_groups(groups, context):
    """Validate without silently altering segment order or repetitions."""
    if not isinstance(groups, dict):
        raise ValueError(f"{context}: expected corpus-to-groups dictionary")
    for corpus, rows in groups.items():
        if not isinstance(corpus, str) or not corpus or not isinstance(rows, list):
            raise ValueError(f"{context}: invalid corpus or group list")
        for row in rows:
            if not isinstance(row, list) or not row:
                raise ValueError(f"{context}: invalid empty or non-list word group")
            for word in row:
                if (not isinstance(word, str) or len(word) < 9
                        or word[0] not in ("o", "n")
                        or not word[1:9].isdigit()):
                    raise ValueError(f"{context}: invalid original-word ID {word!r}")
    return groups


def apply_word_edits(entry, decision):
    # Generic, reversible changes to exact source groups: no special cases
    # for particular books, entity names, or types of referents.
    for field in LINK_FIELDS:
        occurrence = entry["occurrences"][field]
        for corpus, groups in checked_groups(
                decision.get(f"remove_{field}", {}),
                f"{entry['source_id']} {field} removal").items():
            present = occurrence.get(corpus, [])
            for group in groups:
                if group not in present:
                    raise ValueError(
                        f"{entry['source_id']}: absent group cannot be removed: {group}")
                present.remove(group)
        for corpus, groups in checked_groups(
                decision.get(f"add_{field}", {}),
                f"{entry['source_id']} {field} addition").items():
            present = occurrence.setdefault(corpus, [])
            for group in groups:
                if group in present:
                    raise ValueError(
                        f"{entry['source_id']}: source group already exists: {group}")
                present.append(group)
    references = entry["references"]
    for ref in decision.get("remove_references", []):
        if not isinstance(ref, str) or len(ref) != 8 or not ref.isdigit():
            raise ValueError(f"{entry['source_id']}: invalid removed verse reference")
        if references.count(ref) != 1:
            raise ValueError(
                f"{entry['source_id']}: cannot remove missing or non-unique verse: {ref}")
        references.remove(ref)
    for ref in decision.get("add_references", []):
        if not isinstance(ref, str) or len(ref) != 8 or not ref.isdigit():
            raise ValueError(f"{entry['source_id']}: invalid added verse reference")
        if ref in references:
            raise ValueError(f"{entry['source_id']}: verse already referenced: {ref}")
        references.append(ref)



def build(source_root: Path, source_lock: dict, editorial: dict,
          source_absences: dict | None = None,
          source_verse_absences: dict | None = None,
          reference_qualifications: dict | None = None) -> dict:
    if source_lock.get("schema_version") != 1 or editorial.get("schema_version") != 1:
        raise ValueError("Unsupported lock or editorial decision schema")
    decisions = {}
    for decision in editorial["decisions"]:
        original_id = decision["source_id"]
        if original_id in decisions:
            raise ValueError(f"Duplicate editorial decision for {original_id}")
        if decision["action"] not in ("quarantine", "replace_identity", "amend_occurrences"):
            raise ValueError(f"Unsupported action for {original_id}")
        if not decision.get("reason") or not decision.get("evidence"):
            raise ValueError(f"Missing editorial justification or evidence: {original_id}")
        decisions[original_id] = decision

    originals = []
    # Hash every original JSON byte stream, in a deterministic relative-path
    # order. A Git commit label alone does not detect a modified worktree.
    source_manifest = hashlib.sha256()
    for dirname, prefix in CATEGORIES.items():
        folder = source_root / dirname / "json"
        if not folder.is_dir():
            raise ValueError(f"Missing source category: {folder}")
        for path in sorted(folder.glob("*.json")):
            raw = path.read_bytes()
            record = json.loads(raw)
            source_id = record.get("id")
            if source_id != f"{prefix}:{path.stem}":
                raise ValueError(f"Source ID/path disagreement: {path} ({source_id})")
            rel = path.relative_to(source_root).as_posix().encode("utf-8")
            raw_hash = hashlib.sha256(raw).digest()
            source_manifest.update(len(rel).to_bytes(4, "big"))
            source_manifest.update(rel)
            source_manifest.update(raw_hash)
            originals.append((record, raw_hash.hex()))
    source_snapshot_sha256 = source_manifest.hexdigest()
    locked_snapshot = source_lock.get("source_snapshot_sha256")
    if locked_snapshot is not None:
        if (not isinstance(locked_snapshot, str)
                or len(locked_snapshot) != 64
                or any(c not in "0123456789abcdef" for c in locked_snapshot)):
            raise ValueError("Invalid pinned original JSON snapshot SHA-256")
        if locked_snapshot != source_snapshot_sha256:
            raise ValueError(
                "Original JSON source snapshot digest mismatch: "
                f"locked {locked_snapshot}; actual {source_snapshot_sha256}")
    expected = source_lock["source_records_expected"]
    if len(originals) != expected:
        raise ValueError(f"Incomplete source snapshot: {len(originals)} entries; expected {expected}")
    original_ids = {record["id"] for record, _ in originals}
    if len(original_ids) != len(originals):
        raise ValueError("Repeated original entity ID")
    if unknown := set(decisions) - original_ids:
        raise ValueError(f"Editorial decisions target nonexistent records: {sorted(unknown)}")

    new_ids = {
        source_id: decision.get("id", source_id)
        for source_id, decision in decisions.items()
        if decision["action"] == "replace_identity"
    }
    entries = []
    quarantined = []
    for original, raw_hash in originals:
        source_id = original["id"]
        decision = decisions.get(source_id)
        action = decision["action"] if decision else "retain_source_candidate"
        if action == "quarantine":
            quarantined.append({
                "source_id": source_id,
                "source_sha256": raw_hash,
                "reason": decision["reason"],
                "evidence": decision["evidence"],
            })
            continue
        original_primary = original.get("primary_id", source_id)
        entity_id = new_ids.get(source_id, source_id)
        canonical_id = new_ids.get(original_primary, original_primary)
        if decision and decision.get("canonical_id"):
            canonical_id = decision["canonical_id"]
        kind = (decision.get("kind") if decision else None) or entity_id.split(":", 1)[0]
        refs = original.get("references", [])
        if not isinstance(refs, list) or any(
                not isinstance(ref, str) or len(ref) != 8 or not ref.isdigit()
                for ref in refs):
            raise ValueError(f"{source_id}: malformed verse references")
        occurrences = {
            field: checked_groups(
                json.loads(json.dumps(original.get(field, {}))),
                f"{source_id}:{field}")
            for field in LINK_FIELDS
        }
        entry = {
            "id": entity_id,
            "kind": kind,
            "canonical_id": canonical_id,
            "source_id": source_id,
            "source_primary_id": original_primary,
            "source_sha256": raw_hash,
            "review_status": "editorially_reviewed" if decision else "source_unreviewed",
            "references": list(refs),
            "key_references": original.get("key_references", []),
            "occurrences": occurrences,
        }
        if decision:
            if action in ("replace_identity", "amend_occurrences"):
                apply_word_edits(entry, decision)
            entry["editorial_evidence"] = decision["evidence"]
            entry["editorial_reason"] = decision["reason"]
        entries.append(entry)

    return finalize_index(entries, quarantined, source_lock, source_absences,
                          source_verse_absences, reference_qualifications,
                          source_snapshot_sha256, len(originals))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Local immutable snapshot of the ACAI repository")
    parser.add_argument("--lock", type=Path, default=(Path(__file__).resolve().parents[1] / "data" / "source.lock.json"))
    parser.add_argument("--decisions", type=Path, default=(Path(__file__).resolve().parents[1] / "data" / "editorial-decisions.json"))
    parser.add_argument("--source-absences", type=Path,
                        default=(Path(__file__).resolve().parents[1] / "data" / "source-unattested-words.json"),
                        help="Pinned source-word audit evidence; only affects derived lookup")
    parser.add_argument("--source-verse-absences", type=Path,
                        default=(Path(__file__).resolve().parents[1] / "data" / "source-unattested-verses.json"),
                        help="Edition-specific pinned original-word verse inventory evidence")
    parser.add_argument("--reference-qualifications", type=Path,
                        default=(Path(__file__).resolve().parents[1] / "data" / "source-reference-qualifications.json"),
                        help="Pinned source-specific textual variant/subscription claim receipts")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-source-commit", action="store_true",
                        help="Require the local Git HEAD to equal the source lock")
    args = parser.parse_args()
    lock = read_json(args.lock)
    if args.verify_source_commit:
        if not lock.get("source_snapshot_sha256"):
            raise SystemExit(
                "Pinned source verification requires a source_snapshot_sha256 lock")
        import subprocess
        actual = subprocess.check_output(
            ["git", "-C", str(args.source), "rev-parse", "HEAD"], text=True).strip()
        if actual != lock["source_commit"]:
            raise SystemExit(f"Wrong pinned source revision: {actual}")
        worktree = subprocess.check_output(
            ["git", "-C", str(args.source), "status", "--porcelain",
             "--untracked-files=all"], text=True)
        if worktree.strip():
            raise SystemExit(
                "Pinned source checkout has modified or untracked files; "
                "do not build against a dirty source snapshot")
    result = build(args.source, lock, read_json(args.decisions),
                   read_json(args.source_absences),
                   read_json(args.source_verse_absences),
                   read_json(args.reference_qualifications))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8")
    print(json.dumps(result["statistics"], sort_keys=True))


if __name__ == "__main__":
    main()
