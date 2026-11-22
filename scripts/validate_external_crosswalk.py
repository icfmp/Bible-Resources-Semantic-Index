#!/usr/bin/env python3
"""Check source-edition crosswalks without fetching, guessing or publishing.

Structural fields follow links/schema.v1.json. This policy validator adds
native-identity referential integrity and explicit ambiguity accounting.
A reviewed marker is a human editorial claim, never an automatic inference.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_native_entity_builder", ROOT / "scripts" / "build_native_index.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)

COMMIT = re.compile(r"[0-9a-f]{40}\Z")
CROSSWALK_FOLDERS = ("dictionaries", "encyclopedias")
DIRECTORY_KIND = {"dictionaries": "dictionary", "encyclopedias": "encyclopedia"}


def _string(value, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a nonempty string")
    return value


def _fields(value, rule: dict, location: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be an object")
    missing = set(rule["required"]) - set(value)
    unknown = set(value) - set(rule["properties"])
    if missing or unknown:
        raise ValueError(f"{location} fields: missing={sorted(missing)}, unknown={sorted(unknown)}")


def _evidence(items, location: str) -> None:
    if not isinstance(items, list) or not items:
        raise ValueError(f"{location} requires explicit nonempty source evidence")
    for i, item in enumerate(items):
        _string(item, f"{location}[{i}]")


def _allowed(schema: dict, *path):
    result = schema
    for key in path:
        result = result[key]
    return result


def validate(document: dict, active_ids: set[str], schema: dict) -> dict:
    """Fail closed on unsupported mapping identities and unreviewed guesses."""
    _fields(document, schema, "crosswalk")
    if document["schema_version"] != 1:
        raise ValueError("Unsupported external crosswalk schema version")

    resource_schema = schema["properties"]["resource"]
    resource = document["resource"]
    _fields(resource, resource_schema, "resource")
    for key in ("id", "edition", "license", "revision"):
        _string(resource[key], "resource." + key)
    if resource["kind"] not in resource_schema["properties"]["kind"]["enum"]:
        raise ValueError("Unknown external resource kind")
    _string(resource["source_url"], "resource.source_url")
    parsed = urlsplit(resource["source_url"])
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname
            or parsed.username or parsed.password):
        raise ValueError("Resource must provide a concrete HTTP(S) edition source URL")

    provenance_schema = schema["properties"]["provenance"]
    provenance = document["provenance"]
    _fields(provenance, provenance_schema, "provenance")
    _string(provenance["bsi_version"], "provenance.bsi_version")
    if not isinstance(provenance["bsi_source_commit"], str) or not COMMIT.fullmatch(
            provenance["bsi_source_commit"]):
        raise ValueError("Crosswalk must pin a full BRSI producer commit SHA")
    if provenance["review_policy"] != "manual_source_verified":
        raise ValueError("External resource links require manual source review")

    rule = schema["properties"]["links"]["items"]
    allowed_relations = set(rule["properties"]["relation"]["enum"])
    links = document["links"]
    if not isinstance(links, list):
        raise ValueError("links must be a list")
    seen_links = set()
    seen_reviewed_pairs = set()
    for i, link in enumerate(links):
        label = f"links[{i}]"
        _fields(link, rule, label)
        identity = _string(link["entity_id"], label + ".entity_id")
        if identity not in active_ids or identity.startswith("keyterm:"):
            raise ValueError(f"{label} points to an absent, quarantined or restricted BRSI entity: {identity}")
        entry = _string(link["entry_id"], label + ".entry_id")
        relation = link["relation"]
        if relation not in allowed_relations or link["review_status"] != "reviewed":
            raise ValueError(f"{label} is not an independently reviewed, allowed mapping")
        _evidence(link["evidence"], label + ".evidence")
        if "notes" in link and not isinstance(link["notes"], str):
            raise ValueError(f"{label}.notes must be text")
        duplicate = (identity, entry, relation)
        if duplicate in seen_links:
            raise ValueError(f"Duplicate reviewed external mapping: {duplicate}")
        pair = (identity, entry)
        if pair in seen_reviewed_pairs:
            raise ValueError(f"Conflicting reviewed relations for external entry: {pair}")
        seen_reviewed_pairs.add(pair)
        seen_links.add(duplicate)

    abstentions = document.get("abstentions", [])
    if not isinstance(abstentions, list):
        raise ValueError("abstentions must be a list")
    abst_rule = schema["properties"]["abstentions"]["items"]
    allowed_reasons = set(abst_rule["properties"]["reason"]["enum"])
    seen_abstentions = set()
    for i, item in enumerate(abstentions):
        label = f"abstentions[{i}]"
        _fields(item, abst_rule, label)
        identity = _string(item["entity_id"], label + ".entity_id")
        if identity not in active_ids or identity.startswith("keyterm:"):
            raise ValueError(f"{label} points to an absent, quarantined or restricted BRSI entity: {identity}")
        reason = item["reason"]
        if reason not in allowed_reasons or item["review_status"] != "withheld":
            raise ValueError(f"{label} must give a supported reason and withheld status")
        candidates = item["candidate_entry_ids"]
        if not isinstance(candidates, list):
            raise ValueError(f"{label}.candidate_entry_ids must be a list")
        for j, entry in enumerate(candidates):
            _string(entry, f"{label}.candidate_entry_ids[{j}]")
        if len(set(candidates)) != len(candidates):
            raise ValueError(f"Duplicate external candidate in {label}")
        if reason == "ambiguous_entries" and len(candidates) < 2:
            raise ValueError("Ambiguous source entries require at least two candidates")
        if reason == "source_entry_missing" and candidates:
            raise ValueError("A missing source entry cannot assert existing candidates")
        _evidence(item["evidence"], label + ".evidence")
        if "notes" in item and not isinstance(item["notes"], str):
            raise ValueError(f"{label}.notes must be text")
        conflicting_entries = set(candidates) & {entry for linked_id, entry, _ in seen_links if linked_id == identity}
        if conflicting_entries:
            raise ValueError(f"{label} conflicts with reviewed external mapping: {sorted(conflicting_entries)}")
        duplicate = (identity, reason, tuple(sorted(candidates)))
        if duplicate in seen_abstentions:
            raise ValueError(f"Duplicate withheld external mapping: {duplicate}")
        seen_abstentions.add(duplicate)

    return {
        "resource_id": resource["id"],
        "edition": resource["edition"],
        "revision": resource["revision"],
        "kind": resource["kind"],
        "reviewed_links": len(links),
        "withheld_mappings": len(abstentions),
    }


def active_identity_ids(data: Path) -> set[str]:
    index = native.build(data)  # Validates source lock and every canonical entity.
    return {entry["id"] for entry in index["entities"]}


def validate_files(files: list[Path], data: Path) -> list[dict]:
    schema = native.read(ROOT / "links" / "schema.v1.json")
    ids = active_identity_ids(data)
    seen_editions = set()
    summaries = []
    for path in sorted(files):
        result = validate(native.read(path), ids, schema)
        if path.parent.name in DIRECTORY_KIND and result["kind"] != DIRECTORY_KIND[path.parent.name]:
            raise ValueError(f"Crosswalk kind does not match directory: {path}")
        edition_key = (result["resource_id"], result["kind"],
                       result["edition"], result["revision"])
        if edition_key in seen_editions:
            raise ValueError(f"Duplicate edition mapping across files: {path}")
        seen_editions.add(edition_key)
        summaries.append({"file": path.as_posix(), **result})
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--file", type=Path, action="append", default=[])
    parser.add_argument("--scan", action="store_true",
                        help="Check all direct reviewed mapping files in links/dictionaries and links/encyclopedias")
    args = parser.parse_args()
    files = list(args.file)
    if args.scan or not files:
        for folder in CROSSWALK_FOLDERS:
            files.extend(sorted((ROOT / "links" / folder).glob("*.json")))
    results = validate_files(files, args.data)
    print(json.dumps({"crosswalk_files_checked": len(results),
                      "crosswalks": results}, sort_keys=True))


if __name__ == "__main__":
    main()
