#!/usr/bin/env python3
"""Inspect exactly pinned historical BRSI release ZIPs, locally and read-only.

This is a *consumer feasibility check*, not an application integration, a
publisher, an endorsement of underlying third-party rights, or permission
to substitute development UBS indexes for their public projections.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_original_release_lock", ROOT / "scripts" / "verify_historical_asset.py")
historical = importlib.util.module_from_spec(spec)
spec.loader.exec_module(historical)

PUBLIC_SHAPES = {
    "entities": ("format", "bible-entity-index", "entities"),
    "ubs_greek": ("schema", "bsi.ubs-greek-word-crosswalk.v1", "by_word_id"),
    "ubs_hebrew": ("format", "bsi-ubs-hebrew-lexical-crosswalk", "by_macula_word"),
}


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"Duplicate archive JSON field: {key}")
        obj[key] = value
    return obj


def _reject_nonfinite(token):
    raise ValueError(f"Nonstandard archive JSON value: {token}")


def _read_json(payload: bytes, name: str) -> dict:
    try:
        value = json.loads(payload, object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_nonfinite)
    except (UnicodeError, ValueError) as exc:
        raise ValueError(f"Invalid {name} in published archive: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Published {name} is not a JSON object")
    return value


def _archive_files(raw: bytes) -> tuple[dict[str, bytes], str]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if not names or len(set(names)) != len(names):
                raise ValueError("Missing or duplicate archive members")
            for info in infos:
                path = info.filename
                if (path.startswith("/") or "\\" in path or
                        any(part in ("", ".", "..") for part in path.split("/")
                            if not (part == "" and path.endswith("/"))) or
                        info.flag_bits & 0x1):
                    raise ValueError(f"Unsafe or encrypted archive member: {path}")
            if archive.testzip() is not None:
                raise ValueError("ZIP member CRC failed")
            expected = [name for name in names if name.split("/")[-1] == "index.json"]
            if len(expected) != 1:
                raise ValueError("Exactly one source index.json required")
            index_name = expected[0]
            prefix = index_name[:-len("index.json")]
            if prefix + "manifest.json" not in names:
                raise ValueError("Published index has no adjacent manifest.json")
            files = {name[len(prefix):]: archive.read(name)
                     for name in (index_name, prefix + "manifest.json")}
            return files, prefix
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid ZIP archive") from exc


def inspect(kind: str, raw: bytes, lock: dict) -> dict:
    """Check exact historical bytes first; then verify readable public shape."""
    historical.verify_bytes(kind, raw, lock)
    files, prefix = _archive_files(raw)
    index = _read_json(files["index.json"], "index.json")
    manifest = _read_json(files["manifest.json"], "manifest.json")
    format_field, expected_format, map_field = PUBLIC_SHAPES[kind]
    if index.get(format_field) != expected_format:
        raise ValueError(f"Unexpected published {kind} index format")
    lookup = index.get(map_field)
    if not isinstance(lookup, list if kind == "entities" else dict):
        raise ValueError(f"Published {kind} missing its expected lookup collection")
    if kind == "entities":
        profile = index.get("distribution_profile")
        if (not isinstance(profile, dict)
                or profile.get("excluded_kinds") != ["keyterm"]):
            raise ValueError("Published entity index does not exclude Key Terms")
        if any(not isinstance(row, dict) or row.get("kind") == "keyterm"
               or str(row.get("id", "")).startswith("keyterm:")
               for row in lookup):
            raise ValueError("Published entity index exposes restricted Key Terms or malformed entities")
        identifiers = [row.get("id") for row in lookup]
        if (any(not isinstance(entity_id, str) or not entity_id
                for entity_id in identifiers)
                or len(set(identifiers)) != len(lookup)):
            raise ValueError("Published entity identities are absent or duplicated")
        entity_ids = set(identifiers)
        reverse = index.get("by_word")
        if not isinstance(reverse, dict):
            raise ValueError("Published entity original-word lookup is missing")
        for token, candidates in reverse.items():
            if not isinstance(token, str) or not isinstance(candidates, list):
                raise ValueError("Malformed published entity reverse lookup")
            if any(not isinstance(row, dict)
                   or not isinstance(row.get("entity_id"), str)
                   or row["entity_id"].startswith("keyterm:")
                   or row["entity_id"] not in entity_ids
                   for row in candidates):
                raise ValueError("Restricted or malformed entity reverse candidate")
    elif kind == "ubs_greek":
        if (index.get("version") != "0.1.0"
                or index.get("contextual_semantics_independently_verified") is not False):
            raise ValueError("Greek publication falsely approves contextual senses")
    else:
        publication = index.get("publication")
        if (type(index.get("schema_version")) is not int
                or index["schema_version"] != 1
                or not isinstance(index.get("by_strong"), dict)
                or not isinstance(index.get("by_sdbh"), dict)
                or not isinstance(publication, dict)
                or publication.get("version") != "1.0.0"
                or type(publication.get("contextual_senses_inferred")) is not int
                or publication["contextual_senses_inferred"] != 0):
            raise ValueError("Hebrew release schema or sense-approval boundary changed")
    actual_index_hash = hashlib.sha256(files["index.json"]).hexdigest()
    if manifest.get("sha256") is not None and manifest["sha256"] != actual_index_hash:
        raise ValueError("Published index SHA-256 differs from manifest")
    receipts = manifest.get("files")
    if isinstance(receipts, dict) and "index.json" in receipts:
        receipt = receipts["index.json"]
        if (not isinstance(receipt, dict)
                or receipt.get("sha256") != actual_index_hash
                or receipt.get("bytes") != len(files["index.json"])):
            raise ValueError("Published archive internal index receipt mismatch")
    return {
        "kind": kind,
        "release_tag": lock["releases"][kind]["tag"],
        "release_sha256": lock["releases"][kind]["sha256"],
        "archive_prefix": prefix,
        "payload_format": expected_format,
        "lookup_records": len(lookup),
        "local_byte_integrity_verified": True,
        "new_release_created": False,
        "bible_app_modified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entities", type=Path, required=True,
                        help="Downloaded original BSI-0.1.0.zip")
    parser.add_argument("--greek", type=Path, required=True,
                        help="Downloaded original BSI-UBS-Greek-0.1.0.zip")
    parser.add_argument("--hebrew", type=Path, required=True,
                        help="Downloaded original BSI-UBSHebrew-0.9.4-v1.0.0.zip")
    args = parser.parse_args()
    lock = _read_json(historical.LOCK.read_bytes(), "historical-assets.lock.json")
    result = {
        "status": "verified_existing_public_assets_only",
        "artifacts": [
            inspect(kind, path.read_bytes(), lock)
            for kind, path in (
                ("entities", args.entities),
                ("ubs_greek", args.greek),
                ("ubs_hebrew", args.hebrew),
            )
        ],
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
