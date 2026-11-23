#!/usr/bin/env python3
"""Validate source-pinned, case-by-case identity decisions without inventing words.

A review disposition is not a text change: it may explicitly retain a contextual
key, a contested identification, or an indirect referent. Only independently
corroborated positive direct witnesses can change the original-word index.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

KINDS = {
    "deity": "deities", "fauna": "fauna", "flora": "flora",
    "group": "groups", "person": "people", "place": "places",
    "realia": "realia",
}
CLASSIFICATIONS = {
    "contextual_not_direct",
    "uncertain_not_promoted",
    "false_original_name_match",
    "geographical_inference_not_direct",
    "indirect_original_referent",
    "direct_witness_restored",
    "wrong_identity_keys_removed",
    "wrong_contextual_key_corrected",
    "constructed_tribal_territory_no_source_key",
}
BCV8 = re.compile(r"[0-9]{8}\Z")
WORDS = {
    "wlc": re.compile(r"o[0-9]{12}\Z"),
    "SBLGNT": re.compile(r"n[0-9]{11}\Z"),
}
RESTORED_ACTION = "restore_verified_direct_original_word_after_identity_corroboration"


def _must(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _before_key_receipts(record: dict) -> set[str]:
    values: set[str] = set(record["key_references"])
    for change in record["bsi"].get("editorial_field_changes", []):
        previous = change.get("replaced_field_values", {}).get("before", {})
        current = change.get("replaced_field_values", {}).get("after", {})
        for state in (previous, current):
            keys = state.get("key_references", [])
            if isinstance(keys, list):
                values.update(x for x in keys if isinstance(x, str))
    return values


def _collect_pinned_originals(wanted: dict[str, dict], paths: dict[str, Path],
                              existing_indirect: dict[str, set[str]]) -> None:
    for corpus, path in paths.items():
        if corpus not in WORDS:
            raise ValueError(f"Unexpected original corpus: {corpus}")
        found: set[str] = set()
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            _must({"xml:id", "english", "gloss", "lemma"}.issubset(
                reader.fieldnames or []), f"Missing original TSV columns in {path}")
            for row in reader:
                word_id = row["xml:id"]
                evidence = wanted.get(word_id)
                if (evidence is None or evidence["corpus"] != corpus) and (
                        word_id not in existing_indirect.get(corpus, set())):
                    continue
                _must(word_id not in found, f"Duplicate pinned original word {word_id}")
                found.add(word_id)
                if evidence is not None and evidence["corpus"] == corpus:
                    for key in ("lemma", "english", "gloss"):
                        _must(row[key] == evidence[key],
                              f"{word_id}: pinned original {key} mismatch")
        expected = ({word_id for word_id, row in wanted.items()
                     if row["corpus"] == corpus} |
                    existing_indirect.get(corpus, set()))
        _must(expected == found, f"Missing pinned original words in {corpus}: "
              f"{sorted(expected - found)}")


def validate(data_dir: Path, review_path: Path,
             pinned: dict[str, Path] | None = None) -> dict:
    source_lock = json.loads((data_dir / "source.lock.json").read_text("utf-8"))
    review = json.loads(review_path.read_text("utf-8"))
    _must(review.get("schema_version") == 1, "Unsupported review schema")
    _must(isinstance(review.get("reviews"), list), "Missing reviews list")
    _must(review.get("original_sources") == {
        "wlc": source_lock["source_editions"]["wlc"]["edition"],
        "sblgnt": source_lock["source_editions"]["sblgnt"]["edition"],
    }, "Review source pin differs from data/source.lock.json")
    _must(isinstance(review.get("policy"), str) and len(review["policy"]) > 30,
          "Missing review provenance policy")
    seen: set[str] = set()
    words: dict[str, dict] = {}
    indirect_words: dict[str, set[str]] = {"wlc": set(), "SBLGNT": set()}
    counter: Counter[str] = Counter()
    modified: list[str] = []
    for case in review["reviews"]:
        source_id = case.get("source_id")
        _must(isinstance(source_id, str) and source_id.count(":") == 1,
              f"Invalid review source_id: {source_id!r}")
        _must(source_id not in seen, f"Duplicate review {source_id}")
        seen.add(source_id)
        kind, name = source_id.split(":")
        _must(kind in KINDS and name and "/" not in name and ".." not in name,
              f"Unsafe review identity {source_id}")
        record_path = data_dir / "entities" / KINDS[kind] / f"{name}.json"
        _must(record_path.is_file(), f"No source record for {source_id}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        _must(record["id"] == source_id and record["bsi"]["source_id"] == source_id,
              f"Source identity changed for {source_id}")
        _must(re.fullmatch(r"[a-f0-9]{64}", record["bsi"]["source_sha256"]) is not None,
              f"Missing immutable original fingerprint for {source_id}")
        status = case.get("classification")
        _must(status in CLASSIFICATIONS, f"Unrecognized classification for {source_id}")
        counter[status] += 1
        _must(isinstance(case.get("rationale"), str) and len(case["rationale"]) > 50,
              f"No substantial source-specific rationale for {source_id}")
        verses = case.get("reviewed_key_verses")
        constructed = status == "constructed_tribal_territory_no_source_key"
        _must(isinstance(verses, list) and len(set(verses)) == len(verses)
              and all(isinstance(v, str) and BCV8.fullmatch(v) for v in verses),
              f"Invalid review BCV8 verses for {source_id}")
        if constructed:
            _must(kind == "place" and not verses
                  and not record["key_references"] and not record["references"]
                  and not record["explicit_instances"]
                  and "place:Israel" in record.get("subregion_of", []),
                  f"Constructed regional identity has an unsupported lexical claim: {source_id}")
        else:
            _must(bool(verses), f"No reviewed key verse for {source_id}")
            _must(set(verses).issubset(_before_key_receipts(record)),
                  f"Review of {source_id} refers to keys without source or correction receipt")
        witnesses = case.get("original_word_evidence")
        _must(isinstance(witnesses, list), f"Missing candidate evidence list for {source_id}")
        direct_words = {word for groups in record["explicit_instances"].values()
                        for group in groups for word in group}
        links = case.get("existing_indirect_word_links", [])
        _must(isinstance(links, list),
              f"Malformed existing indirect source-word evidence for {source_id}")
        if status == "indirect_original_referent":
            _must(bool(links), f"Missing actual indirect source-word anchor for {source_id}")
        if constructed:
            _must(not links and not witnesses,
                  f"Unattested source geography cannot have lexical witnesses: {source_id}")
        for link in links:
            field = link.get("source_field")
            corpus = link.get("corpus")
            word_id = link.get("word_id")
            _must(field in {"subject_referents", "pronominal_referents"}
                  and corpus in WORDS and isinstance(word_id, str)
                  and WORDS[corpus].fullmatch(word_id) is not None
                  and link.get("verse_id") in verses
                  and word_id[1:9] == link["verse_id"],
                  f"Invalid existing indirect group witness for {source_id}: {link}")
            _must(any(word_id in group
                      for group in record[field].get(corpus, [])),
                  f"Review invents an indirect link absent from source {source_id}: {word_id}")
            _must(word_id not in direct_words,
                  f"Indirect review reuses a direct source token for {source_id}")
            indirect_words[corpus].add(word_id)
        restored = case.get("editorial_outcome") == "source_record_corrected_in_this_review"
        _must(case.get("editorial_outcome") in {
            "source_record_corrected_in_this_review",
            "no_unverified_direct_word_assignment",
        }, f"Invalid outcome for {source_id}")
        if restored:
            receipts = record["bsi"].get("editorial_field_changes", [])
            _must(bool(receipts), f"Missing reversible correction for {source_id}")
            _must(any(ch.get("replaced_field_values", {}).get("before") !=
                      ch.get("replaced_field_values", {}).get("after")
                      for ch in receipts),
                  f"No actual field change for {source_id}")
            modified.append(source_id)
        if status == "direct_witness_restored":
            _must(restored and len(witnesses) > 0,
                  f"Direct repair must cite original words for {source_id}")
            _must(any(ch.get("action") == RESTORED_ACTION
                      for ch in record["bsi"].get("editorial_field_changes", [])),
                  f"Missing independent direct-witness receipt for {source_id}")
        if status in {"wrong_identity_keys_removed", "wrong_contextual_key_corrected"}:
            _must(restored, f"Wrong-key conclusion has no repair: {source_id}")
        for witness in witnesses:
            corpus = witness.get("corpus")
            word_id = witness.get("word_id")
            _must(corpus in WORDS and isinstance(word_id, str)
                  and WORDS[corpus].fullmatch(word_id) is not None,
                  f"Invalid exact original word ID for {source_id}")
            _must(word_id[1:9] == witness.get("verse_id")
                  and witness["verse_id"] in verses,
                  f"Word/verse mismatch for {source_id}: {word_id}")
            for key in ("lemma", "english", "gloss"):
                _must(isinstance(witness.get(key), str), f"{word_id}: missing {key}")
            if status == "direct_witness_restored":
                _must(word_id in direct_words,
                      f"Restored original word missing from direct group for {source_id}: {word_id}")
            if word_id in words:
                existing = words[word_id]
                _must(all(existing[k] == witness[k] for k in
                          ("corpus", "lemma", "english", "gloss")),
                      f"Conflicting original evidence for {word_id}")
            else:
                words[word_id] = witness
    if pinned is not None:
        _must(set(pinned) == set(WORDS), "Both locked source corpora are required")
        _collect_pinned_originals(words, pinned, indirect_words)
    return {
        "reviewed_distinct_entities": len(seen),
        "source_record_corrections": len(modified),
        "classifications": dict(sorted(counter.items())),
        "exact_original_word_evidence": len(words),
        "already_indirect_pinned_word_evidence": sum(map(len, indirect_words.values())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--wlc", type=Path)
    parser.add_argument("--sblgnt", type=Path)
    args = parser.parse_args()
    if (args.wlc is None) != (args.sblgnt is None):
        parser.error("--wlc and --sblgnt must be given together")
    pins = None if args.wlc is None else {"wlc": args.wlc, "SBLGNT": args.sblgnt}
    print("BRSi_SOURCE_KEY_REVIEW " + json.dumps(
        validate(args.data, args.review, pins), sort_keys=True))


if __name__ == "__main__":
    main()
