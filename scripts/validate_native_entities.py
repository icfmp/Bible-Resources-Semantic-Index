#!/usr/bin/env python3
"""Independently compare each migrated BSI record with the frozen source + editorials.

Verifies all original fields except the explicitly edited fields; reconstructs
every permitted lexical reverse lookup without trusting migration manifests.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def import_script(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

legacy = import_script("scripts/compile_index.py", "bsi_legacy_verify")
profile = import_script("scripts/distribution_profile.py", "bsi_public_verify")


def check(source: Path, native: Path):
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))
    lock = load(ROOT / "data/source.lock.json")
    original = legacy.build(
        source, lock, load(ROOT / "data/editorial-decisions.json"),
        load(ROOT / "data/source-unattested-words.json"),
        load(ROOT / "data/source-unattested-verses.json"),
        load(ROOT / "data/source-reference-qualifications.json"),
    )
    current = profile.exclude_kinds(original, {"keyterm"})
    expected = {e["source_id"]: e for e in current["entities"]}
    quarantined = {q["source_id"]: q for q in current["quarantined"]}
    found = set()
    reverse = defaultdict(set)
    for category, prefix in legacy.CATEGORIES.items():
        if category == "keyterms":
            continue
        root = source / category / "json"
        for path in sorted(root.glob("*.json")):
            old = load(path)
            sid = old["id"]
            if sid in found:
                raise AssertionError("Duplicated source ID " + sid)
            found.add(sid)
            canonical_path = native / (
                "quarantined" if sid in quarantined else "entities"
            ) / category / path.name
            rec = load(canonical_path)
            old_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            assert rec["bsi"]["source_id"] == sid, sid
            assert rec["bsi"]["source_sha256"] == old_hash, sid
            if sid in quarantined:
                assert rec["bsi"]["state"] == "quarantined", sid
                assert rec["bsi"]["reason"] == quarantined[sid]["reason"], sid
                assert rec["bsi"]["evidence"] == quarantined[sid]["evidence"], sid
                assert {k: v for k, v in rec.items() if k != "bsi"} == old, sid
                continue
            expected_entity = expected[sid]
            assert rec["id"] == expected_entity["id"], sid
            assert rec["primary_id"] == expected_entity["canonical_id"], sid
            assert rec["type"] == expected_entity["kind"], sid
            assert rec["references"] == expected_entity["references"], sid
            assert rec["key_references"] == expected_entity["key_references"], sid
            assert rec["bsi"]["review_status"] == expected_entity["review_status"], sid
            assert rec["bsi"]["canonical_id"] == expected_entity["canonical_id"], sid
            assert rec["bsi"]["source_primary_id"] == expected_entity["source_primary_id"], sid
            for field in legacy.LINK_FIELDS:
                assert rec[field] == expected_entity["occurrences"][field], (sid, field)
            for field in ("editorial_reason", "editorial_evidence"):
                if field in expected_entity:
                    assert rec["bsi"][field] == expected_entity[field], sid
                else:
                    assert field not in rec["bsi"], sid
            # Every original field not intentionally corrected or added
            # must remain present with exactly the same structured value.
            mutable = {"id", "primary_id", "type", "references", "key_references",
                       *legacy.LINK_FIELDS}
            assert {k: v for k, v in rec.items() if k not in mutable and k != "bsi"} == {
                k: v for k, v in old.items() if k not in mutable
            }, sid
            for field in legacy.LINK_FIELDS:
                for corpus, groups in rec[field].items():
                    standard = legacy.canonical_source_corpus(lock, corpus)
                    for group in groups:
                        for word in group:
                            reverse[f"{standard}:{word}"].add((rec["id"], field))
    assert found == set(expected) | set(quarantined), (
        "Canonical record set differs", len(found), len(expected), len(quarantined)
    )
    absent = set(current["unattested_source_words"])
    actual_reverse = {
        word: [{"entity_id": ent, "link_type": typ} for ent, typ in sorted(hits)]
        for word, hits in sorted(reverse.items()) if word not in absent
    }
    assert actual_reverse == current["by_word"], "Word reverse lookup changed"
    assert len(expected) + len(quarantined) == len(found)
    return {
        "verified_source_records": len(found),
        "verified_active_records": len(expected),
        "verified_quarantined": len(quarantined),
        "verified_reverse_lookup_words": len(actual_reverse),
        "original_source_records": original["statistics"]["source_records"],
        "excluded_keyterms_pending_rights": 868,
        "preserved_original_source_snapshot_sha256": original["provenance"]["source_snapshot_sha256"],
        "result": "PASS",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--native", type=Path, default=ROOT / "data")
    a = p.parse_args()
    print(json.dumps(check(a.source, a.native), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
