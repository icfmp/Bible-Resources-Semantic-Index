#!/usr/bin/env python3
"""Verify every active BRSI original-word ID against frozen Macula TSV inventories.

An original-word ID is a *source observation*, not editorial proof of
which biblical entity the word means. This audit neither creates entity
links nor silently repairs source records or approves lexical senses.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ("explicit_instances", "pronominal_referents", "subject_referents")
CORPUS = {"WLC": "wlc", "wlc": "wlc", "SBLGNT": "sblgnt", "sblgnt": "sblgnt"}


def tsv_word_inventory(path: Path) -> set[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or "xml:id" not in reader.fieldnames:
            raise ValueError(f"Missing exact xml:id Macula TSV column: {path}")
        words: set[str] = set()
        for line_no, row in enumerate(reader, start=2):
            word = row["xml:id"]
            if not isinstance(word, str) or not word:
                raise ValueError(f"Missing source original-word ID: {path}:{line_no}")
            if word in words:
                raise ValueError(f"Duplicate original-word ID: {path}:{line_no}: {word}")
            words.add(word)
    if not words:
        raise ValueError(f"Empty source word inventory: {path}")
    return words


def audit(data: Path, frozen_inventories: dict[str, set[str]]) -> dict:
    lock = json.loads((data / "source.lock.json").read_text(encoding="utf-8"))
    for corpus in ("wlc", "sblgnt"):
        if corpus not in frozen_inventories or not frozen_inventories[corpus]:
            raise ValueError(f"Missing pinned original-word inventory: {corpus}")
    no_words = json.loads((data / "source-unattested-words.json")
                          .read_text(encoding="utf-8"))
    if (no_words.get("corpus") != "wlc"
            or no_words.get("source_edition") != lock["source_editions"]["wlc"]["edition"]):
        raise ValueError("Unattested-word exceptions are not edition-pinned")
    allowed_absent = set(no_words["word_ids"])
    if len(allowed_absent) != len(no_words["word_ids"]):
        raise ValueError("Duplicate source-unattested original word")
    observed: dict[str, set[str]] = defaultdict(set)
    source_claims = Counter()
    misses = []
    invalid_exception_fields = []
    for path in sorted((data / "entities").glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        source_id = record["bsi"]["source_id"]
        for field in FIELDS:
            for corpus_raw, groups in record.get(field, {}).items():
                corpus = CORPUS.get(corpus_raw)
                if corpus is None:
                    raise ValueError(f"Unknown corpus: {path} {field}.{corpus_raw}")
                expected = lock["source_editions"][corpus]
                for group in groups:
                    for word in group:
                        source_claims[(corpus, field)] += 1
                        observed[corpus].add(word)
                        if (not isinstance(word, str)
                                or not word.startswith(expected["word_id_prefix"])
                                or len(word) != len(expected["word_id_prefix"]) + expected["word_id_digits"]
                                or not word[len(expected["word_id_prefix"]):].isascii()
                                or not word[len(expected["word_id_prefix"]):].isdigit()):
                            misses.append({"source_id": source_id, "field": field,
                                           "corpus": corpus, "word": word,
                                           "reason": "invalid_source_word_shape"})
                            continue
                        if word not in frozen_inventories[corpus]:
                            if corpus == "wlc" and word in allowed_absent:
                                if field != "subject_referents":
                                    invalid_exception_fields.append({
                                        "source_id": source_id, "field": field, "word": word})
                            else:
                                misses.append({"source_id": source_id, "field": field,
                                               "corpus": corpus, "word": word,
                                               "reason": "absent_from_exact_pinned_source"})
    absent_not_observed = sorted(allowed_absent - observed["wlc"])
    exception_present_in_source = sorted(allowed_absent & frozen_inventories["wlc"])
    if absent_not_observed or exception_present_in_source:
        raise ValueError(
            f"Stale or contradicted pinned-word exceptions: missing_claims="
            f"{absent_not_observed[:20]}, actually_present={exception_present_in_source[:20]}")
    return {
        "schema_version": 1,
        "source_editions": {k: lock["source_editions"][k]["edition"]
                            for k in ("wlc", "sblgnt")},
        "source_inventory_sizes": {k: len(v)
                                   for k, v in sorted(frozen_inventories.items())},
        "observed_distinct_words": {k: len(v) for k, v in sorted(observed.items())},
        "source_annotation_claims": {f"{corpus}:{field}": count
                                     for (corpus, field), count
                                     in sorted(source_claims.items())},
        "documented_source_word_absences": len(allowed_absent),
        "invalid_exception_usage": invalid_exception_fields,
        "unexpected_missing_words": misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--wlc", type=Path, required=True)
    parser.add_argument("--sblgnt", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.data, {
        "wlc": tsv_word_inventory(args.wlc),
        "sblgnt": tsv_word_inventory(args.sblgnt),
    })
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("unexpected_missing_words", "invalid_exception_usage")},
                     sort_keys=True))
    if result["unexpected_missing_words"] or result["invalid_exception_usage"]:
        print(json.dumps({
            "unexpected_missing_words": result["unexpected_missing_words"][:50],
            "missing_word_count": len(result["unexpected_missing_words"]),
            "invalid_exception_usage": result["invalid_exception_usage"][:50],
        }, sort_keys=True))
        raise SystemExit("Active BRSI word IDs disagree with exact pinned original source")


if __name__ == "__main__":
    main()
