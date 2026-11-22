#!/usr/bin/env python3
"""Verify exact historical Bible-Resources release assets without republishing.

SHA-256 values in release/historical-assets.lock.json were checked against
GitHub Releases asset digests, not inferred from archive filenames.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release" / "historical-assets.lock.json"
KIND_TAGS = {
    "entities": ("bsi-v0.1.0", "BSI-0.1.0.zip"),
    "ubs_greek": ("bsi-ubs-greek-v0.1.0", "BSI-UBS-Greek-0.1.0.zip"),
    "ubs_hebrew": ("bsi-ubs-hebrew-v1.0.0", "BSI-UBSHebrew-0.9.4-v1.0.0.zip"),
}
HASH = re.compile(r"[0-9a-f]{64}\Z")


def verify_lock(lock: dict) -> None:
    if (not isinstance(lock, dict)
            or set(lock) != {"schema_version", "source_repository", "evidence", "releases"}
            or lock["schema_version"] != 1
            or lock["source_repository"] != "icfmp/Bible-Resources"
            or not isinstance(lock["evidence"], str)
            or "2026-11-22" not in lock["evidence"]
            or not isinstance(lock["releases"], dict)
            or set(lock["releases"]) != set(KIND_TAGS)):
        raise ValueError("Unknown or incomplete historical asset lock")
    for kind, record in lock["releases"].items():
        if (not isinstance(record, dict)
                or set(record) != {"tag", "filename", "bytes", "sha256", "historical"}
                or (record["tag"], record["filename"]) != KIND_TAGS[kind]
                or not isinstance(record["bytes"], int)
                or type(record["bytes"]) is not int or record["bytes"] < 1
                or not isinstance(record["sha256"], str)
                or not HASH.fullmatch(record["sha256"])
                or record["historical"] is not True):
            raise ValueError(f"Invalid source-published historical asset lock: {kind}")


def verify_bytes(kind: str, raw: bytes, lock: dict) -> dict:
    verify_lock(lock)
    if kind not in KIND_TAGS:
        raise ValueError("Unknown historical artifact kind")
    record = lock["releases"][kind]
    actual = hashlib.sha256(raw).hexdigest()
    if len(raw) != record["bytes"] or actual != record["sha256"]:
        raise ValueError(f"Historical {kind} release bytes differ from original published asset")
    return {
        "kind": kind, "sha256": actual, "bytes": len(raw),
        "matches_original_gitHub_release": True,
        "source_repository": "icfmp/Bible-Resources",
        "tag": record["tag"], "publication_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=sorted(KIND_TAGS))
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=LOCK)
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    receipt = verify_bytes(args.kind, args.archive.read_bytes(), lock)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
