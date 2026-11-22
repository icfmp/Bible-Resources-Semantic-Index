#!/usr/bin/env python3
"""Audit inherited BSI entity relationships without silently rewriting source values.

Every cross-entity identifier is traced to its exact JSON path. Original source
IDs and reviewed BSI IDs are resolved separately; unresolved and stale links
are reported, never guessed or automatically corrected.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_SOURCE_PREFIXES = ("person", "place", "group", "deity", "fauna", "flora",
                         "realia", "keyterm")
BSI_CATEGORIES = set(KNOWN_SOURCE_PREFIXES) | {"work", "literary_work"}
IDENTITY_PATTERN = re.compile(r"^([A-Za-z][A-Za-z_-]*):(.+)$")
# Keys contain source words/metadata and should never be mistaken for entity links.
EXCLUDED_BRANCHES = {"id", "primary_id", "bsi", "alternate_sources", "localizations", "references",
                     "key_references", "explicit_instances",
                     "pronominal_referents", "subject_referents"}


def walk_links(value, keypath=()):
    if isinstance(value, dict):
        for key, child in value.items():
            if not keypath and key in EXCLUDED_BRANCHES:
                continue
            yield from walk_links(child, (*keypath, key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk_links(child, (*keypath, i))
    elif isinstance(value, str):
        # ACAI group_origin can hold a semicolon-separated set of exact IDs.
        # This is not one missing identity; preserve each source string and
        # report its members separately without rewriting the original field.
        components = [v.strip() for v in value.split(";")]
        matches = [IDENTITY_PATTERN.fullmatch(v) for v in components]
        if all(match and match.group(1) in BSI_CATEGORIES for match in matches):
            for i, item in enumerate(components):
                loc = (*keypath, i) if len(components) > 1 else keypath
                yield {"path": list(loc), "target": item}


def audit(data: Path) -> dict:
    records = []
    for root in ("entities", "quarantined"):
        for path in sorted((data / root).rglob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            meta = doc.get("bsi")
            if not isinstance(meta, dict):
                raise ValueError(f"Missing BSI metadata: {path}")
            records.append((path.relative_to(data).as_posix(), root, doc))
    current, origin = {}, {}
    for path, state, doc in records:
        curr = doc.get("id")
        sid = doc["bsi"].get("source_id")
        if not isinstance(curr, str) or not isinstance(sid, str):
            raise ValueError(f"Bad identity: {path}")
        if curr in current:
            raise ValueError(f"Duplicate current ID {curr}")
        if sid in origin:
            raise ValueError(f"Duplicate original ID {sid}")
        current[curr] = (path, state)
        origin[sid] = (curr, path, state)

    outgoing = Counter()
    examples = defaultdict(list)
    problems = []
    relationships = 0
    for path, state, doc in records:
        # Quarantined originals are evidence, not active cross-reference owners.
        if state != "entities":
            continue
        for link in walk_links(doc):
            target = link["target"]
            info = {
                "source_path": path,
                "source_id": doc["id"],
                "json_path": link["path"],
                "target": target,
            }
            relationships += 1
            if target in current:
                tgt_path, tgt_state = current[target]
                classification = ("current_to_quarantined" if tgt_state == "quarantined"
                                  else "current_identity")
            elif target in origin:
                resolved, tgt_path, tgt_state = origin[target]
                classification = ("old_identity_to_quarantined" if tgt_state == "quarantined"
                                  else "old_identity")
                info["current_candidate"] = resolved
            elif target.startswith("keyterm:"):
                # Restricted keyterm records are separately accounted for by manifest;
                # no claims of nonexistence or automatic license clearance.
                classification = "restricted_keyterm_unavailable"
            else:
                classification = "unresolved_identity"
            info["classification"] = classification
            outgoing[classification] += 1
            if len(examples[classification]) < 20:
                examples[classification].append(info)
            if classification in {"old_identity", "old_identity_to_quarantined",
                                  "unresolved_identity", "current_to_quarantined"}:
                problems.append(info)
    return {
        "schema_version": 1,
        "scope": "source-inherited structured exact-ID fields outside original-word/link/provenance/localization branches",
        "policy": "read_only_no_automatic_correction",
        "records_examined": len(records),
        "structured_relationships": relationships,
        "classifications": dict(sorted(outgoing.items())),
        "examples": dict(sorted(examples.items())),
        "review_candidates": sorted(
            problems, key=lambda v: (v["source_path"], str(v["json_path"]), v["target"])
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--fail-on-unresolved", action="store_true")
    args = parser.parse_args()
    result = audit(args.data)
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("records_examined", "structured_relationships", "classifications")},
                     sort_keys=True))
    print(json.dumps({"review_candidates": result["review_candidates"]},
                     ensure_ascii=False, sort_keys=True))
    if args.fail_on_unresolved and result["classifications"].get("unresolved_identity", 0):
        raise SystemExit("Unresolved cross-entity links require explicit review")


if __name__ == "__main__":
    main()
