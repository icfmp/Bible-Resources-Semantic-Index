#!/usr/bin/env python3
"""Build a deterministic, strictly NONPUBLISHED native BRSI entity ZIP candidate.

This is not a general-purpose lexical packager or a release publisher.
Any future approval needs independent source, rights and editorial review.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_release_contract", ROOT / "scripts" / "release_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)

PREFIX = "BRSI-Entities-0.0.0-local/"
ZIP_DATE = (1980, 1, 1, 0, 0, 0)
CONTENTS = frozenset({"index.json", "source.lock.json", "README.md",
                      "ATTRIBUTION.md", "LICENSE.txt", "manifest.json"})
README = b"""# BRSI Entities - local candidate only

NOT PUBLISHED / NOT APPROVED FOR REDISTRIBUTION.
Offline, source-pinned, original-word-linked biblical identity index.
Use exact original-language word IDs and retain ambiguous/unreviewed
source identities. This index includes no language-localized biographies
or the 868 prohibited ACAI Key Terms. Reader-facing names need
independent editorial and rights clearance.

The archive is deliberately restricted to the BRSI native entity profile.
This is not a lexical UBS Greek/Hebrew distribution or a Bible app feature.
See the source repository docs/RELEASE_CONTRACT.md for approval gates.
"""
ATTRIBUTION = b"""# Source attribution and transformation notice (candidate)

BRSI entity data adapt ACAI Biblical Entity Data (CC BY-SA 4.0).
Source: https://github.com/icfmp/ACAI
Original BiblioNexus and Mission Mutual credits must be retained.
The exact ACAI revision/snapshot hash is in source.lock.json.

Source-original word IDs refer to MACULA WLC and SBLGNT edition locks.
MACULA data: CC BY 4.0 (Clear-Bible / Biblica source notices).
No original Bible text, UBS dictionary prose, licensed lexical
definitions or entire original MACULA token annotations are packaged.

BRSI transformations include reviewed identity fixes, exclusion of
restricted Key Terms and source-conditioned original-word mappings.
No upstream organization endorses this derivative candidate.
Rights verification and explicit owner authorization are required
separately for any actual release.
"""
LICENSE = b"""Candidate data adaptation: CC BY-SA 4.0 International
https://creativecommons.org/licenses/by-sa/4.0/

ACAI source entity data: CC BY-SA 4.0.
MACULA source original-word identifiers: source dataset CC BY 4.0.
Not an assertion of permission to distribute separate original texts,
dictionary contents or third-party annotations.
This candidate is NOT approved for publication.
"""


def file_receipts(files: dict[str, bytes]) -> dict:
    return {name: {"sha256": contract.digest(blob), "bytes": len(blob)}
            for name, blob in sorted(files.items())}


def make_candidate(index_raw: bytes, lock: dict, producer_revision: str) -> tuple[bytes, dict]:
    # Source-specific scope and forbidden category validation occurs first.
    receipt = contract.make_local_receipt(
        "entities", index_raw, producer_revision, lock)
    if index_raw != contract.canonical_json(contract.load_json(index_raw)):
        raise ValueError("Native entity index must use canonical deterministic JSON")
    files = {
        "index.json": index_raw,
        "source.lock.json": contract.canonical_json(lock),
        "README.md": README,
        "ATTRIBUTION.md": ATTRIBUTION,
        "LICENSE.txt": LICENSE,
    }
    manifest = {
        "schema_version": 1,
        "contract": "brsi.entity-candidate.v1",
        "kind": "entities",
        "version": "0.0.0-local",
        "producer_revision": producer_revision,
        "publication": {"status": "candidate_unapproved", "approved": False,
                        "tag": None},
        "source_editions": receipt["source_editions"],
        "files": file_receipts(files),
        "excluded_categories": ["keyterm"],
        "rights": {"license": "CC BY-SA 4.0", "redistribution_cleared": False},
    }
    files["manifest.json"] = contract.canonical_json(manifest)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for name, payload in sorted(files.items()):
            info = zipfile.ZipInfo(PREFIX + name, date_time=ZIP_DATE)
            info.create_system = 3
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    raw = buf.getvalue()
    external = copy.deepcopy(receipt)
    external["artifact"] = {
        "filename": "BRSI-Entities-0.0.0-local.zip",
        "sha256": contract.digest(raw),
        "bytes": len(raw),
        "input_class": "nonpublishing_entity_zip_candidate",
    }
    contract.validate_manifest(external)
    verify_candidate(raw, external)
    return raw, external


def verify_candidate(raw: bytes, receipt: dict) -> dict:
    contract.verify_bytes(receipt, raw)
    if (receipt["kind"] != "entities"
            or receipt["publication"]["status"] != "candidate_unapproved"
            or receipt["artifact"]["input_class"] != "nonpublishing_entity_zip_candidate"
            or receipt["rights"]["redistribution_cleared"]):
        raise ValueError("Not a nonpublishing entity ZIP candidate receipt")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        info = archive.infolist()
        paths = [x.filename for x in info]
        if len(paths) != len(set(paths)) or set(paths) != {PREFIX + x for x in CONTENTS}:
            raise ValueError("Unexpected or duplicate ZIP members")
        for entry in info:
            if (entry.date_time != ZIP_DATE or entry.create_system != 3
                    or entry.external_attr >> 16 != 0o644
                    or entry.compress_type != zipfile.ZIP_DEFLATED
                    or entry.is_dir()):
                raise ValueError("Nondeterministic or unsafe ZIP member")
        files = {name: archive.read(PREFIX + name) for name in CONTENTS}
    manifest_raw = files.pop("manifest.json")
    manifest = contract.load_json(manifest_raw)
    if manifest_raw != contract.canonical_json(manifest):
        raise ValueError("Noncanonical internal candidate manifest")
    if (set(manifest) != {
            "schema_version", "contract", "kind", "version", "producer_revision",
            "publication", "source_editions", "files", "excluded_categories", "rights"}
            or manifest["schema_version"] != 1
            or manifest["contract"] != "brsi.entity-candidate.v1"
            or manifest["kind"] != "entities"
            or manifest["version"] != "0.0.0-local"
            or manifest["producer_revision"] != receipt["producer_revision"]
            or manifest["publication"] != {
                "status": "candidate_unapproved", "approved": False, "tag": None}
            or manifest["source_editions"] != receipt["source_editions"]
            or manifest["excluded_categories"] != ["keyterm"]
            or manifest["rights"] != {
                "license": "CC BY-SA 4.0", "redistribution_cleared": False}
            or manifest["files"] != file_receipts(files)):
        raise ValueError("Altered internal candidate manifest or member digests")
    lock = contract.load_json(files["source.lock.json"])
    contract.validate_local_payload("entities", files["index.json"], lock)
    if files["index.json"] != contract.canonical_json(contract.load_json(files["index.json"])):
        raise ValueError("Noncanonical native entity payload")
    if files["README.md"] != README or files["ATTRIBUTION.md"] != ATTRIBUTION or files["LICENSE.txt"] != LICENSE:
        raise ValueError("Unexpected unreviewed license/readme content")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage")
    stage.add_argument("--index", type=Path, required=True)
    stage.add_argument("--lock", type=Path, default=ROOT / "data/source.lock.json")
    stage.add_argument("--producer-revision", required=True)
    stage.add_argument("--output", type=Path, required=True)
    stage.add_argument("--receipt", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--archive", type=Path, required=True)
    verify.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "stage":
        files = (args.index, args.lock)
        if (args.output.resolve() in {p.resolve() for p in files}
                or args.receipt.resolve() in {p.resolve() for p in files}
                or args.output.resolve() == args.receipt.resolve()):
            parser.error("Outputs must not overwrite inputs or each other")
        raw, receipt = make_candidate(
            args.index.read_bytes(), contract.load_json(args.lock.read_bytes()),
            args.producer_revision)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
        args.receipt.write_bytes(contract.canonical_json(receipt))
        print(json.dumps({"status": "candidate_unapproved",
                          "zip_sha256": contract.digest(raw), "zip_bytes": len(raw)},
                         sort_keys=True))
    else:
        receipt = contract.load_json(args.receipt.read_bytes())
        verify_candidate(args.archive.read_bytes(), receipt)
        print(json.dumps({"verified": True, "publication_approved": False},
                         sort_keys=True))


if __name__ == "__main__":
    main()
