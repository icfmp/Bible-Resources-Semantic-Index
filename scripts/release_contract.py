#!/usr/bin/env python3
"""Nonpublishing BRSI artifact integrity and future pinned-consumption contract.

Local receipts are NOT release approvals. Source-pinned lexical development
baselines must never be treated as public lexical distributions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "icfmp/Bible-Resources-Semantic-Index"
KINDS = {"entities", "ubs_greek", "ubs_hebrew"}
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?\Z")
TAG = re.compile(r"brsi-(?:entities|ubs-greek|ubs-hebrew)-v[0-9]+\.[0-9]+\.[0-9]+\Z")
CONTRACT = "brsi.artifact.v1"
LICENSE = "CC BY-SA 4.0"
SOURCE_GREEK = "8423afe47b9e8f24b7772e808af45c7159a6fe7e"
SOURCE_HEBREW = "47db250bd55d0d8577f2a94fba114ef16c35b23c"
SOURCE_UBS = "a15a96cfaa4ca18a6c0339016645ba1e534db3c8"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def exact_keys(value: object, expected: set[str], name: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"Invalid {name} fields: expected {sorted(expected)}")


def load_json(raw: bytes) -> dict:
    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"Duplicate JSON key: {key}")
            obj[key] = value
        return obj
    obj = json.loads(raw, object_pairs_hook=unique_pairs)
    if not isinstance(obj, dict):
        raise ValueError("Expected a JSON object")
    return obj


def source_editions(kind: str, acai_lock: dict) -> list[dict]:
    if acai_lock.get("source_commit") is None or not SHA40.fullmatch(acai_lock["source_commit"]):
        raise ValueError("Missing pinned original ACAI source commit")
    if kind not in KINDS:
        raise ValueError("Unknown BRSI kind")
    records = {
        "acai": {
            "name": "ACAI", "revision": acai_lock["source_commit"],
            "edition": "Biblical Entity Data pinned JSON",
            "license": LICENSE, "url": "https://github.com/icfmp/ACAI",
        },
        "macula_greek": {
            "name": "MACULA SBLGNT", "revision": SOURCE_GREEK,
            "edition": "SBLGNT token IDs", "license": "CC BY 4.0",
            "url": "https://github.com/Clear-Bible/macula-greek",
        },
        "macula_hebrew": {
            "name": "MACULA WLC", "revision": SOURCE_HEBREW,
            "edition": "WLC token IDs", "license": "CC BY 4.0",
            "url": "https://github.com/Clear-Bible/macula-hebrew",
        },
        "ubs_greek": {
            "name": "UBS Greek Dictionary", "revision": SOURCE_UBS,
            "edition": "1.0 EN/FR", "license": LICENSE,
            "url": "https://github.com/ubsicap/ubs-open-license",
        },
        "ubs_hebrew": {
            "name": "UBS Hebrew Dictionary", "revision": SOURCE_UBS,
            "edition": "0.9.4 EN/FR", "license": LICENSE,
            "url": "https://github.com/ubsicap/ubs-open-license",
        },
    }
    keys = {
        "entities": ("acai", "macula_greek", "macula_hebrew"),
        "ubs_greek": ("ubs_greek", "macula_greek"),
        "ubs_hebrew": ("ubs_hebrew", "macula_hebrew"),
    }
    return [records[key] for key in keys[kind]]


def forbidden_keyterm(value: object) -> bool:
    if isinstance(value, dict):
        return any(forbidden_keyterm(k) or forbidden_keyterm(v)
                   for k, v in value.items())
    if isinstance(value, list):
        return any(forbidden_keyterm(v) for v in value)
    return isinstance(value, str) and value.startswith("keyterm:")


def validate_local_payload(kind: str, raw: bytes, lock: dict) -> str:
    obj = load_json(raw)
    if kind == "entities":
        if (obj.get("schema_version") != 1
                or obj.get("distribution_profile", {}).get("excluded_kinds") != ["keyterm"]
                or obj.get("distribution_profile", {}).get("name") != "bsi-v0.1-without-keyterms"
                or obj.get("provenance", {}).get("source_snapshot_sha256") !=
                lock.get("source_snapshot_sha256")
                or not isinstance(obj.get("entities"), list)):
            raise ValueError("Not the current keyterm-free native entity index")
        if forbidden_keyterm(obj):
            raise ValueError("Restricted ACAI Key Term present in entity candidate")
        return "bsi.native-entity-index.v1"
    profile = {"ubs_greek": "bsi-ubs-greek-lexical-crosswalk",
               "ubs_hebrew": "bsi-ubs-hebrew-lexical-crosswalk"}
    if kind not in profile or obj.get("format") != profile[kind] or obj.get("schema_version") != 1:
        raise ValueError("Not a pinned UBS lexical development baseline")
    dictionary, macula = obj.get("dictionary", {}), obj.get("macula", {})
    expected_macula = SOURCE_GREEK if kind == "ubs_greek" else SOURCE_HEBREW
    if (dictionary.get("revision") != SOURCE_UBS or
            macula.get("revision") != expected_macula):
        raise ValueError("Lexical baseline source revisions drifted")
    # These checked-in lexical baselines may hold fields not approved for
    # redistribution. This validates their identity only, NOT export rights.
    return f"{profile[kind]}.v1"


def make_local_receipt(kind: str, raw: bytes, source_revision: str,
                       lock: dict, version: str = "0.0.0-local") -> dict:
    if kind not in KINDS or not isinstance(source_revision, str) or not SHA40.fullmatch(source_revision):
        raise ValueError("Kind and exact BRSI Git commit are mandatory")
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("Malformed artifact version")
    if not raw:
        raise ValueError("Empty artifact")
    profile = validate_local_payload(kind, raw, lock)
    is_entity = kind == "entities"
    manifest = {
        "contract": CONTRACT,
        "schema_version": 1,
        "kind": kind,
        "payload_schema": profile,
        "version": version,
        "producer_revision": source_revision,
        "source_editions": source_editions(kind, lock),
        "rights": {
            "data_license": LICENSE,
            "attribution": "Source credits and component licenses: docs/RIGHTS_AND_INTEGRITY.md",
            "redistribution_cleared": False,
            "excluded_keyterms": True,
        },
        "artifact": {
            "filename": f"{kind}-local-index.json",
            "sha256": digest(raw),
            "bytes": len(raw),
            "input_class": (
                "native_keyterm_free_index" if is_entity
                else "checked_in_nonpublic_lexical_baseline"
            ),
        },
        "publication": {
            "status": "candidate_unapproved" if is_entity else "local_integrity_only",
            "approved": False, "tag": None, "repository": REPO,
        },
    }
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict) -> None:
    exact_keys(manifest, {
        "contract", "schema_version", "kind", "payload_schema", "version",
        "producer_revision", "source_editions", "rights", "artifact", "publication",
    }, "manifest")
    if manifest["contract"] != CONTRACT or manifest["schema_version"] != 1:
        raise ValueError("Unknown artifact contract schema")
    kind = manifest["kind"]
    if kind not in KINDS:
        raise ValueError("Unknown artifact kind")
    if not isinstance(manifest["payload_schema"], str) or not manifest["payload_schema"]:
        raise ValueError("Missing format/schema identity")
    if not isinstance(manifest["version"], str) or not VERSION.fullmatch(manifest["version"]):
        raise ValueError("Invalid version")
    if not isinstance(manifest["producer_revision"], str) or not SHA40.fullmatch(manifest["producer_revision"]):
        raise ValueError("Producer revision must be an immutable SHA")
    sources = manifest["source_editions"]
    if not isinstance(sources, list) or len(sources) < 2:
        raise ValueError("Missing original source editions")
    names = []
    for entry in sources:
        exact_keys(entry, {"name", "revision", "edition", "license", "url"}, "source edition")
        if (not isinstance(entry["name"], str) or not entry["name"].strip()
                or not isinstance(entry["revision"], str) or not SHA40.fullmatch(entry["revision"])
                or not all(isinstance(entry[k], str) and entry[k].strip()
                           for k in ("edition", "license", "url"))
                or not entry["url"].startswith("https://")):
            raise ValueError("Invalid original source metadata")
        names.append(entry["name"])
    if len(set(names)) != len(names):
        raise ValueError("Duplicate source editions")
    rights = manifest["rights"]
    exact_keys(rights, {"data_license", "attribution", "redistribution_cleared",
                        "excluded_keyterms"}, "rights")
    if (rights["data_license"] != LICENSE
            or not isinstance(rights["attribution"], str)
            or len(rights["attribution"].strip()) < 10
            or type(rights["redistribution_cleared"]) is not bool
            or rights["excluded_keyterms"] is not True):
        raise ValueError("Source attribution or redistribution constraints missing")
    artifact = manifest["artifact"]
    exact_keys(artifact, {"filename", "sha256", "bytes", "input_class"}, "artifact")
    filename = artifact["filename"]
    if (not isinstance(filename, str)
            or not re.fullmatch(r"[A-Za-z0-9._-]+\.(?:json|zip)", filename)
            or filename.startswith(".") or ".." in filename
            or not isinstance(artifact["sha256"], str)
            or not SHA64.fullmatch(artifact["sha256"])
            or type(artifact["bytes"]) is not int or artifact["bytes"] <= 0):
        raise ValueError("Unsafe artifact filename or invalid fingerprint")
    if artifact["input_class"] not in {
            "native_keyterm_free_index", "nonpublishing_entity_zip_candidate",
            "checked_in_nonpublic_lexical_baseline", "source_reviewed_public_projection"}:
        raise ValueError("Unknown artifact input class")
    pub = manifest["publication"]
    exact_keys(pub, {"status", "approved", "tag", "repository"}, "publication")
    if pub["repository"] != REPO or type(pub["approved"]) is not bool:
        raise ValueError("Unknown publisher or invalid approval")
    if pub["status"] == "owner_approved_release":
        if (pub["approved"] is not True or not rights["redistribution_cleared"]
                or artifact["input_class"] != "source_reviewed_public_projection"
                or not isinstance(pub["tag"], str) or not TAG.fullmatch(pub["tag"])
                or not filename.endswith(".zip")
                or not pub["tag"].startswith("brsi-" + kind.replace("_", "-").replace("entities", "entities") + "-v")):
            raise ValueError("Release metadata missing approval or allowlisted public projection")
        if not pub["tag"].endswith("-v" + manifest["version"]):
            raise ValueError("Release tag/version mismatch")
    elif pub["status"] in {"candidate_unapproved", "local_integrity_only"}:
        if (pub["approved"] is not False or pub["tag"] is not None
                or rights["redistribution_cleared"]):
            raise ValueError("Local receipts must never claim publication approval")
        if kind == "entities":
            candidates = {
                "native_keyterm_free_index": ".json",
                "nonpublishing_entity_zip_candidate": ".zip",
            }
            if (pub["status"] != "candidate_unapproved"
                    or artifact["input_class"] not in candidates
                    or not filename.endswith(candidates[artifact["input_class"]])):
                raise ValueError("Invalid nonpublishing entity candidate")
        elif (artifact["input_class"] != "checked_in_nonpublic_lexical_baseline"
              or pub["status"] != "local_integrity_only"
              or not filename.endswith(".json")):
            raise ValueError("Private baseline cannot be promoted to public candidate")
    else:
        raise ValueError("Unknown publication status")


def verify_bytes(manifest: dict, raw: bytes, *, expected_sha256: str | None = None,
                 expected_version: str | None = None,
                 expected_revision: str | None = None,
                 expected_tag: str | None = None,
                 require_release: bool = False) -> None:
    validate_manifest(manifest)
    if digest(raw) != manifest["artifact"]["sha256"] or len(raw) != manifest["artifact"]["bytes"]:
        raise ValueError("Artifact checksum/byte count mismatch")
    if require_release:
        if (manifest["publication"]["status"] != "owner_approved_release"
                or expected_sha256 is None or expected_version is None
                or expected_revision is None or expected_tag is None):
            raise ValueError("Pinned approved release version, SHA, tag and producer revision required")
    if expected_tag is not None and manifest["publication"]["tag"] != expected_tag:
        raise ValueError("Artifact does not match consumer-pinned release tag")
    if expected_sha256 is not None and manifest["artifact"]["sha256"] != expected_sha256:
        raise ValueError("Artifact does not match consumer-pinned SHA-256")
    if expected_version is not None and manifest["version"] != expected_version:
        raise ValueError("Artifact does not match consumer-pinned version")
    if expected_revision is not None and manifest["producer_revision"] != expected_revision:
        raise ValueError("Artifact does not match consumer-pinned producer revision")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_subparsers(dest="command", required=True)
    stage = cmd.add_parser("local-receipt", help="never copies or publishes private data")
    stage.add_argument("--kind", choices=sorted(KINDS), required=True)
    stage.add_argument("--input", type=Path, required=True)
    stage.add_argument("--lock", type=Path, default=ROOT / "data/source.lock.json")
    stage.add_argument("--producer-revision", required=True)
    stage.add_argument("--version", default="0.0.0-local")
    stage.add_argument("--output", type=Path, required=True)
    verify = cmd.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--artifact", type=Path, required=True)
    verify.add_argument("--expected-sha256")
    verify.add_argument("--expected-version")
    verify.add_argument("--expected-revision")
    verify.add_argument("--expected-tag")
    verify.add_argument("--require-release", action="store_true")
    args = parser.parse_args()
    if args.command == "local-receipt":
        if args.input.resolve() == args.output.resolve():
            parser.error("Must not overwrite source input")
        manifest = make_local_receipt(
            args.kind, args.input.read_bytes(), args.producer_revision,
            json.loads(args.lock.read_text(encoding="utf-8")), args.version)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(manifest))
        print(json.dumps({"kind": args.kind, "status": manifest["publication"]["status"],
                          "sha256": manifest["artifact"]["sha256"],
                          "bytes": manifest["artifact"]["bytes"]}, sort_keys=True))
    else:
        manifest = load_json(args.manifest.read_bytes())
        verify_bytes(manifest, args.artifact.read_bytes(),
                     expected_sha256=args.expected_sha256,
                     expected_version=args.expected_version,
                     expected_revision=args.expected_revision,
                     expected_tag=args.expected_tag,
                     require_release=args.require_release)
        print(json.dumps({"verified": True, "kind": manifest["kind"],
                          "published": manifest["publication"]["approved"]}, sort_keys=True))


if __name__ == "__main__":
    main()
