#!/usr/bin/env python3
"""Read-only candidate witnesses for unanchored, Bible-flagged ACAI places.

Only the exact Macula original-word source edition may supply identifiers.
English matching helps *locate a witness for human review*; it is not
a source-verified entity identification and cannot mutate native records.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

BOOKS_HEBREW = range(1, 40)
BOOKS_GREEK = range(40, 67)
FINAL_QUALIFIER = re.compile(r"\s+\([^()]*\)$")


def normalize_name(s: str) -> str:
    value = unicodedata.normalize("NFKD", s.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def source_candidate_places(data: Path) -> list[dict]:
    candidates = []
    for path in sorted((data / "entities" / "places").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if (record.get("mentioned_in_bible") is not True
                or record.get("references") or record.get("explicit_instances")):
            continue
        label = record["localizations"]["eng"]["preferred_label"]
        base = FINAL_QUALIFIER.sub("", label).strip()
        candidates.append({
            "source_id": record["bsi"]["source_id"],
            "label": label,
            "query_name": normalize_name(base),
            "key_references": record["key_references"],
            "only_mentioned_in_apocrypha":
                record.get("only_mentioned_in_apocrypha", False),
        })
    return candidates


def source_word_evidence(records: list[dict], source_paths: dict[str, Path]) -> dict:
    needed: dict[str, set[str]] = defaultdict(set)
    for row in records:
        for verse in row["key_references"]:
            book = int(verse[:2])
            if book in BOOKS_HEBREW:
                needed["wlc"].add(verse)
            elif book in BOOKS_GREEK:
                needed["sblgnt"].add(verse)
    evidence: dict[str, list[dict]] = defaultdict(list)
    for corpus in ("wlc", "sblgnt"):
        with source_paths[corpus].open(encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle, delimiter="\t")
            if not {"xml:id", "english", "gloss", "lemma", "text"}.issubset(
                    set(rows.fieldnames or [])):
                raise ValueError(f"Missing original Macula source columns: {corpus}")
            for original in rows:
                word = original["xml:id"]
                if not word or word[1:9] not in needed[corpus]:
                    continue
                evidence[word[1:9]].append({
                    "corpus": corpus, "word_id": word,
                    "english": original["english"],
                    "gloss": original["gloss"],
                    "lemma": original["lemma"],
                    "text": original["text"],
                })
    return dict(evidence)


def triage(records: list[dict], words_by_verse: dict[str, list[dict]]) -> dict:
    result = []
    counts = defaultdict(int)
    for rec in records:
        matches = []
        for verse in rec["key_references"]:
            for word in words_by_verse.get(verse, []):
                en = normalize_name(word["english"])
                gl = normalize_name(word["gloss"])
                if en == rec["query_name"] or gl == rec["query_name"]:
                    strength = "exact_english_or_gloss_candidate_only"
                elif (rec["query_name"] and
                      (rec["query_name"] in en.split() or rec["query_name"] in gl.split())):
                    strength = "contains_name_candidate_only"
                else:
                    continue
                matches.append({
                    "verse_id": verse, "word_id": word["word_id"],
                    "english": word["english"], "gloss": word["gloss"],
                    "text": word["text"], "lemma": word["lemma"],
                    "evidence": strength,
                })
        status = (
            "matching_original_word_candidate_review_required" if matches
            else "apocrypha_not_in_pinned_66_book_corpora"
            if rec["only_mentioned_in_apocrypha"]
            else "no_english_gloss_candidate_review_original_text_manually")
        counts[status] += 1
        result.append({**rec, "status": status,
                       "matching_source_words": matches})
    return {"policy": "source_original_word_candidates_only_no_automatic_mapping",
            "counts": dict(sorted(counts.items())),
            "cases": result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--wlc", type=Path, required=True)
    parser.add_argument("--sblgnt", type=Path, required=True)
    parser.add_argument("--max-cases", type=int, default=150)
    args = parser.parse_args()
    candidates = source_candidate_places(args.data)
    words = source_word_evidence(
        candidates, {"wlc": args.wlc, "sblgnt": args.sblgnt})
    report = triage(candidates, words)
    print(json.dumps({"counts": report["counts"],
                      "sample_count": len(report["cases"])}, sort_keys=True))
    for row in report["cases"][:args.max_cases]:
        print("PLACE_SOURCE_CANDIDATE " + json.dumps(row, sort_keys=True,
                                                        ensure_ascii=False))


if __name__ == "__main__":
    main()
