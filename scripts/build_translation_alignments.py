#!/usr/bin/env python3
"""Pinned, nonpublishing translation-alignment importer (not a lexical dictionary).

Consumes original Scripture Burrito 0.3-style alignment groups and token TSVs
without modifying any input. Output is an edition-qualified *candidate* lookup.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


SOURCE_ID = re.compile(r"^(?:[no])?[0-9]{11,12}$")
TARGET_ID = re.compile(r"^[0-9]{11,12}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    def invalid_constant(value):
        raise ValueError(f"invalid JSON constant: {value}")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=strict_object, parse_constant=invalid_constant)


def canonical_json(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def gzip_payload(data: bytes) -> bytes:
    """Reproducible gzip payload: no timestamp or producer filename."""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9,
                       filename="", mtime=0) as archive:
        archive.write(data)
    return buffer.getvalue()


def digest(path: Path, expected: dict):
    raw = path.read_bytes()
    if "size" in expected and len(raw) != expected["size"]:
        raise ValueError(f"{path}: input size differs from pinned source")
    sha = hashlib.sha256(raw).hexdigest()
    if not SHA256.fullmatch(expected.get("sha256") or ""):
        raise ValueError(f"{path}: missing or malformed pinned SHA-256")
    if sha != expected["sha256"]:
        raise ValueError(f"{path}: SHA-256 differs from pinned source")
    # Git blob SHA-1 protects the pinned original bytes until SHA-256 is recorded.
    git_sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if not SHA1.fullmatch(expected["git_blob_sha"]) or git_sha != expected["git_blob_sha"]:
        raise ValueError(f"{path}: Git blob differs from pinned source")
    return {"sha256": sha, "git_blob_sha": git_sha, "size": len(raw)}


def corpus_id(raw: str, canon: str, is_source: bool) -> str | None:
    if raw == "MISSING":
        return None
    if not isinstance(raw, str):
        return None
    if is_source:
        if not SOURCE_ID.fullmatch(raw):
            return None
        digits = raw[1:] if raw[:1] in ("n", "o") else raw
        prefix = "o" if canon == "ot" else "n"
        if raw[:1] in ("n", "o") and raw[0] != prefix:
            return None
    else:
        if not TARGET_ID.fullmatch(raw):
            return None
        digits = raw
    book, chapter, verse = int(digits[:2]), int(digits[2:5]), int(digits[5:8])
    lo, hi = (1, 39) if canon == "ot" else (40, 66)
    if not lo <= book <= hi or not 1 <= chapter <= 150 or not 1 <= verse <= 176:
        return None
    if not 1 <= int(digits[8:11]) <= 999:
        return None
    # An explicit final subword-part must be a nonzero positive ordinal.
    if len(digits) == 12 and digits[11] == "0":
        return None
    return (("o" if canon == "ot" else "n") + digits) if is_source else digits


def verse_id(token_id: str) -> str:
    value = token_id[1:] if token_id[:1] in ("o", "n") else token_id
    return value[:8]


def token_census(path: Path, canon: str, is_source: bool):
    # Independent IDs, not words or phrases; source text and gloss never exported.
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or not ({"id", "identifier"} & set(reader.fieldnames)):
            raise ValueError(f"{path}: absent token ID column")
        field = "id" if "id" in reader.fieldnames else "identifier"
        result = set()
        for number, row in enumerate(reader, start=2):
            value = row.get(field)
            canonical = corpus_id(value, canon, is_source)
            if canonical is None:
                raise ValueError(f"{path}:{number}: invalid token ID {value!r}")
            if canonical in result:
                raise ValueError(f"{path}:{number}: duplicate token ID {canonical}")
            result.add(canonical)
    return result


def selectors(values, canon, source):
    if not isinstance(values, list):
        raise ValueError("selectors must be lists")
    # Multiple attestations are not automatically duplicates or errors; a
    # duplicate selector *inside one group* is an invalid array.
    if len(values) != len(set(map(repr, values))):
        raise ValueError("duplicate selector in one alignment group")
    return [corpus_id(value, canon, source) for value in values]


def apply_corrections(raw, locator, corrections):
    correction = corrections.get(locator)
    if correction is None:
        return raw, False
    for part in ("source", "target"):
        if raw.get(part) != correction["expected"][part]:
            raise ValueError(f"{locator}: correction original witness changed")
    if not correction.get("evidence") or not all(
        isinstance(s, str) and s.strip() for s in correction["evidence"]
    ):
        raise ValueError(f"{locator}: missing independently reviewed correction evidence")
    # Only a separate, auditable projection is corrected; the upstream input
    # and original selectors remain present in the exported row.
    return {**raw, **correction["replacement"]}, True


def build(manifest, corrections_doc, upstream_root: Path):
    if manifest.get("schema_version") != 1 or not SHA1.fullmatch(manifest.get("revision", "")):
        raise ValueError("missing exact upstream commit lock")
    if corrections_doc.get("schema_version") != 1 or not isinstance(corrections_doc.get("corrections"), list):
        raise ValueError("invalid correction ledger")
    corrections = {}
    for c in corrections_doc["corrections"]:
        locator = c.get("locator")
        if (not isinstance(locator, str) or locator in corrections
                or set(c.get("expected", {})) != {"source", "target"}
                or set(c.get("replacement", {})) != {"source", "target"}):
            raise ValueError("invalid or duplicate correction")
        corrections[locator] = c
    files = {item["key"]: item for item in manifest["inputs"]}
    receipts = {}
    for key, item in files.items():
        name = item["path"]
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("unsafe upstream path")
        receipts[key] = digest(upstream_root / name, item)
    indexes = {}
    used_corrections = set()
    for group in manifest["groups"]:
        canon = group["canon"]
        source_file, target_file, alignment_file = (files[group[field]] for field in
                                                      ("source", "target", "alignment"))
        source_ids = token_census(upstream_root / source_file["path"], canon, True)
        target_ids = token_census(upstream_root / target_file["path"], canon, False)
        target_census_complete = bool(target_ids)
        alignment = read_json(upstream_root / alignment_file["path"])
        if not isinstance(alignment, dict) or not isinstance(alignment.get("records"), list):
            raise ValueError("not a Scripture Burrito alignment-group document")
        if not isinstance(alignment.get("meta"), dict) or alignment.get("type") != "translation":
            raise ValueError("alignment missing group metadata or translation type")
        documents = alignment.get("documents")
        if (not isinstance(documents, list) or len(documents) != 2
                or not all(isinstance(doc, dict) and isinstance(doc.get("docid"), str)
                           for doc in documents)):
            raise ValueError("alignment missing source/target document declarations")
        if [doc["docid"] for doc in documents] != [group["source_docid"], group["target_docid"]]:
            raise ValueError("alignment document editions disagree with manifest")
        if alignment.get("roles") != ["source", "target"]:
            raise ValueError("alignment source/target roles absent, reversed or ambiguous")
        stats = Counter()
        by_source = defaultdict(list)
        by_target = defaultdict(list)
        rows = []
        aligned_source = set()
        aligned_target = set()
        overlapping_source = Counter()
        overlapping_target = Counter()
        problem_by_book = defaultdict(Counter)
        for number, original in enumerate(alignment["records"]):
            if not isinstance(original, dict):
                raise ValueError(f"{canon}: record {number} not an object")
            locator = f"{canon}:{number}"
            record, changed = apply_corrections(original, locator, corrections)
            if changed:
                used_corrections.add(locator)
            for part in ("source", "target"):
                if part not in record:
                    raise ValueError(f"{locator}: missing {part} selector array")
            raw_source, raw_target = original["source"], original["target"]
            src = selectors(record["source"], canon, True)
            tgt = selectors(record["target"], canon, False)
            problems = []
            if not src or not tgt or any(x is None for x in src + tgt):
                problems.append("missing_or_invalid_selector")
            if any(x not in source_ids for x in src):
                problems.append("source_token_unattested")
            if target_census_complete:
                if any(x not in target_ids for x in tgt):
                    problems.append("target_token_unattested")
            else:
                problems.append("target_census_unavailable")
            verses = {verse_id(x) for x in src + tgt if x is not None}
            if len(verses) > 1:
                problems.append("cross_verse_selector")
            # Source-relative BCV and target-relative BCV must be kept distinct
            # if genuinely different; no inferred versification conversion.
            if not src and tgt:
                problems.append("no_source_anchor")
            if not tgt and src:
                problems.append("no_target_anchor")
            topology = ("unresolved" if not src or not tgt else
                        ("one_to_one" if len(src) == len(tgt) == 1 else
                         "one_to_many" if len(src) == 1 else
                         "many_to_one" if len(tgt) == 1 else "many_to_many"))
            status = "unresolved" if any(p != "target_census_unavailable" for p in problems) else (
                "target_unverified" if problems else "source_attested")
            for source in (x for x in src if x is not None):
                by_source[source].append(number)
                aligned_source.add(source)
                overlapping_source[source] += 1
            for target in (x for x in tgt if x is not None):
                by_target[target].append(number)
                aligned_target.add(target)
                overlapping_target[target] += 1
            upstream_id = original.get("meta", {}).get("id") if isinstance(original.get("meta"), dict) else None
            row = {
                "ordinal": number,
                "upstream_id": upstream_id,
                "original_record_meta": original.get("meta", {}),
                "source_ids_original": raw_source,
                "target_ids_original": raw_target,
                "source_ids": record["source"],
                "target_ids": record["target"],
                "source_lookup_ids": src,
                "target_lookup_ids": tgt,
                "topology": topology,
                "validation": status,
                "problems": problems,
                "origin": record.get("meta", {}).get("origin", alignment["meta"].get("origin"))
                          if isinstance(record.get("meta", {}), dict) else None,
                "independently_reviewed": False,
                "correction_applied": changed,
            }
            rows.append(row)
            stats[status] += 1
            stats["topology_" + topology] += 1
            for problem in problems:
                stats["problem_" + problem] += 1
                anchors = [x for x in src + tgt if x is not None]
                book = verse_id(anchors[0])[:2] if anchors else "unknown"
                problem_by_book[problem][book] += 1
        if set(corrections) != used_corrections and canon == manifest["groups"][-1]["canon"]:
            raise ValueError("unused corrections in ledger")
        stats["records"] = len(rows)
        stats["source_tokens"] = len(source_ids)
        stats["source_tokens_aligned"] = len(aligned_source & source_ids)
        stats["source_tokens_unaligned"] = len(source_ids - aligned_source)
        stats["source_tokens_multiple_groups"] = sum(v > 1 for v in overlapping_source.values())
        stats["target_tokens"] = len(target_ids) if target_census_complete else None
        stats["target_tokens_aligned"] = len(aligned_target & target_ids) if target_census_complete else None
        stats["target_tokens_unaligned"] = len(target_ids - aligned_target) if target_census_complete else None
        stats["target_tokens_multiple_groups"] = sum(v > 1 for v in overlapping_target.values())
        stats["target_census_complete"] = target_census_complete
        indexes[canon] = {
            "format": "brsi-translation-alignment-candidate",
            "schema_version": 1,
            "resource_id": manifest["resource_id"],
            "upstream_revision": manifest["revision"],
            "canon": canon,
            "source_edition": group["source_edition"],
            "target_edition": manifest["target_edition"],
            "source_id_scheme": "MACULA BCVW(P) (corpus-qualified)",
            "target_id_scheme": "BCVW(P) token ordinal; edition-specific",
            "alignment_type": alignment["type"],
            "original_documents": alignment["documents"],
            "original_roles": alignment["roles"],
            "original_group_meta": alignment["meta"],
            "records": rows,
            "by_source": dict(sorted(by_source.items())),
            "by_target": dict(sorted(by_target.items())),
            "coverage": dict(sorted(stats.items())),
            "problem_counts_by_book": {k: dict(sorted(v.items())) for k, v in sorted(problem_by_book.items())},
            "rights_status": "private_candidate_no_publication",
        }
    if set(corrections) != used_corrections:
        raise ValueError("unused corrections in ledger")
    return indexes, receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    indexes, receipts = build(manifest, read_json(args.corrections), args.upstream_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for canon, index in sorted(indexes.items()):
        data = canonical_json(index)
        path = args.output_dir / (canon + ".json")
        path.write_bytes(data)
        compressed = gzip_payload(data)
        (args.output_dir / (canon + ".json.gz")).write_bytes(compressed)
        outputs[canon] = {"sha256": hashlib.sha256(data).hexdigest(),
                          "size": len(data),
                          "gzip_sha256": hashlib.sha256(compressed).hexdigest(),
                          "gzip_size": len(compressed),
                          "coverage": index["coverage"],
                          "problem_counts_by_book": index["problem_counts_by_book"]}
    receipt = {
        "schema_version": 1,
        "upstream_revision": manifest["revision"],
        "input_integrity": dict(sorted(receipts.items())),
        "candidate_outputs": outputs,
        "publication_approved": False,
    }
    (args.output_dir / "receipt.json").write_bytes(canonical_json(receipt))
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
