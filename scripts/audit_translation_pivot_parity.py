#!/usr/bin/env python3
"""Audit token-coordinate and lemma parity across independent pinned MACULA editions.

This is a nonpublishing evidence census, not a remapper or a lexical/sense
identity validator. Equal BCV token IDs or lemmas cannot certify a translation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def read_json(path):
    def reject(value):
        raise ValueError(f"invalid JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=strict_object, parse_constant=reject)


def normalized_id(value, canon):
    if not isinstance(value, str):
        raise ValueError("non-string original token ID")
    digits = value[1:] if value[:1] in ("n", "o") else value
    prefix = "n" if canon == "nt" else "o"
    if (value[:1] in ("n", "o") and value[0] != prefix
            or not re.fullmatch(r"[0-9]{11,12}", digits)
            or (len(digits) == 12 and digits[11] == "0")):
        raise ValueError(f"unsupported original token ID: {value}")
    book = int(digits[:2])
    if not ((40 <= book <= 66) if canon == "nt" else (1 <= book <= 39)):
        raise ValueError(f"outside expected corpus: {value}")
    return prefix + digits


def collect_source(path, canon, id_field, lemma_field):
    """Preserve an original source's IDs exactly, but count lemmas without export."""
    source = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if not reader.fieldnames or not {id_field, lemma_field}.issubset(reader.fieldnames):
            raise ValueError(f"{path}: missing pinned token/lemma columns")
        for n, row in enumerate(reader, start=2):
            value = row[id_field]
            wid = normalized_id(value, canon)
            if wid in source:
                raise ValueError(f"{path}:{n}: duplicated ID {wid}")
            lemma = row[lemma_field]
            if lemma is None:
                raise ValueError(f"{path}:{n}: malformed lemma column")
            source[wid] = lemma
    if not source:
        raise ValueError(f"{path}: empty original-source corpus")
    return source


def expected_integrity(path, sha):
    if not re.fullmatch(r"[0-9a-f]{64}", str(sha)):
        raise ValueError(f"unlocked SHA-256 for {path}")
    actual = sha256(Path(path))
    if actual != sha:
        raise ValueError(f"{path}: pinned source SHA-256 changed")
    return actual


def per_book(ids):
    return dict(sorted(Counter(value[1:3] for value in ids).items()))


def compare(canon, source, pivot, aligned):
    aligned = set(aligned)
    if not aligned <= source.keys():
        raise ValueError(f"{canon}: some candidate aligned IDs absent from their own Clear.Bible source")
    all_source = set(source)
    all_pivot = set(pivot)
    common = all_source & all_pivot
    linked_shared = aligned & all_pivot
    aligned_without_pivot = aligned - all_pivot
    # Exact spelling comparison is evidence, *not* a contextual equivalence decision.
    lemma_equal = lemma_different = lemma_missing = 0
    different_lemma_ids = set()
    for wid in sorted(linked_shared):
        left = source[wid]
        right = pivot[wid]
        if not left or not right:
            lemma_missing += 1
        elif unicodedata.normalize("NFC", left) == unicodedata.normalize("NFC", right):
            lemma_equal += 1
        else:
            lemma_different += 1
            different_lemma_ids.add(wid)
    return {
        "canon": canon,
        "source_tokens_clear_bible": len(all_source),
        "source_tokens_brsi_macula": len(all_pivot),
        "original_ids_present_in_both": len(common),
        "clear_bible_only_original_ids": len(all_source - all_pivot),
        "brsi_macula_only_original_ids": len(all_pivot - all_source),
        "original_ids_linked_to_lsg": len(aligned),
        "linked_ids_present_in_brsi_macula": len(linked_shared),
        "linked_ids_absent_from_brsi_macula": len(aligned_without_pivot),
        "linked_same_id_lemma_nfc_equal": lemma_equal,
        "linked_same_id_lemma_nfc_different": lemma_different,
        "linked_same_id_lemma_unavailable": lemma_missing,
        "mismatch_by_book": {
            "linked_id_absent": per_book(aligned_without_pivot),
            "linked_id_lemma_different": per_book(different_lemma_ids),
            "clear_bible_only_ids": per_book(all_source - all_pivot),
            "brsi_macula_only_ids": per_book(all_pivot - all_source),
        },
        "identity_certified": False,
        "contextual_senses_certified": False,
        "target_lsg_edition_certified": False,
    }


def audit(alignment_manifest, candidate_receipt, source_paths, candidate_paths, pivot_manifest, pivot_paths):
    if alignment_manifest["revision"] != candidate_receipt["upstream_revision"]:
        raise ValueError("candidate receipt source revision mismatch")
    if pivot_manifest.get("schema_version") != 1:
        raise ValueError("invalid independent MACULA pivot lock")
    expected = {record["key"]: record for record in alignment_manifest["inputs"]}
    actual = {}
    for canon in ("nt", "ot"):
        group = next(g for g in alignment_manifest["groups"] if g["canon"] == canon)
        source_record = expected[group["source"]]
        source_path = Path(source_paths[canon])
        expected_integrity(source_path, source_record["sha256"])
        candidate_path = Path(candidate_paths[canon])
        receipt_row = candidate_receipt["candidate_outputs"][canon]
        expected_integrity(candidate_path, receipt_row["sha256"])
        candidate = read_json(candidate_path)
        if (candidate.get("format") != "brsi-translation-alignment-candidate"
                or candidate.get("schema_version") != 1
                or candidate.get("canon") != canon
                or candidate.get("upstream_revision") != alignment_manifest["revision"]
                or candidate.get("source_edition") != group["source_edition"]):
            raise ValueError(f"{canon}: source-qualified candidate metadata mismatch")
        pivot_lock = pivot_manifest["sources"][canon]
        if not re.fullmatch(r"[0-9a-f]{40}", pivot_lock.get("revision", "")):
            raise ValueError("missing original pivot revision lock")
        pivot_path = Path(pivot_paths[canon])
        pivot_sha = expected_integrity(pivot_path, pivot_lock.get("sha256"))
        source = collect_source(source_path, canon, "id", "lemma")
        pivot = collect_source(pivot_path, canon, "xml:id", "lemma")
        aligned = candidate.get("by_source")
        if not isinstance(aligned, dict):
            raise ValueError(f"{canon}: no candidate by_source index")
        if (len(aligned) != candidate["coverage"]["source_tokens_aligned"]
                or candidate["coverage"]["source_tokens"] != len(source)
                or candidate["coverage"]["records"] != receipt_row["coverage"]["records"]):
            raise ValueError(f"{canon}: candidate counts or linked IDs changed")
        for word, occurrences in aligned.items():
            if word != normalized_id(word, canon) or not isinstance(occurrences, list) or not occurrences:
                raise ValueError(f"{canon}: invalid word lookup")
        result = compare(canon, source, pivot, aligned)
        result["clear_bible_source_sha256"] = sha256(source_path)
        result["brsi_macula_source_revision"] = pivot_lock["revision"]
        result["brsi_macula_source_sha256"] = pivot_sha
        actual[canon] = result
    return {
        "schema_version": 1,
        "audit_kind": "independent-macula-token-ids-and-lemmas",
        "alignment_upstream_revision": alignment_manifest["revision"],
        "canon_audits": actual,
        "publication_authorized": False,
        "note": "Equal token ID and lemma spelling is not proof of exact textual or contextual identity.",
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("alignment-manifest", "candidate-receipt", "nt-source", "ot-source",
                 "nt-candidate", "ot-candidate", "pivot-manifest", "nt-pivot",
                 "ot-pivot", "output"):
        cli.add_argument("--" + name, type=Path, required=True)
    args = vars(cli.parse_args())
    result = audit(
        read_json(args["alignment_manifest"]), read_json(args["candidate_receipt"]),
        {"nt": args["nt_source"], "ot": args["ot_source"]},
        {"nt": args["nt_candidate"], "ot": args["ot_candidate"]},
        read_json(args["pivot_manifest"]),
        {"nt": args["nt_pivot"], "ot": args["ot_pivot"]},
    )
    data = (json.dumps(result, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")
    args["output"].parent.mkdir(parents=True, exist_ok=True)
    args["output"].write_bytes(data)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    print("AUDIT_SHA256=" + hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
