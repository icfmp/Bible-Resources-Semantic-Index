#!/usr/bin/env python3
"""Draw reproducible, text-free, *unreviewed* MACULA-LSG semantic review cases.

This is a case sampler, NOT a semantic aligner, a lexical evaluator, or a
Bible-application export. Reviewers must establish the gold spans separately.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = "brsi-macula-lsg-semantic-review-2000-v1"
STRATA = (
    "aquifer_explicit_non_equivalent_source",
    "other_part_of_same_original_word_has_link",
    "not_present_in_aquifer_source_alignment_records",
    "aquifer_record_source_with_no_uniquely_located_french_word",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rank(seed: str, original_id: str) -> str:
    return digest((seed + "\x00" + original_id).encode("utf-8"))


def coordinates(source_id: str) -> tuple[str, str, str]:
    if not isinstance(source_id, str) or len(source_id) < 10:
        raise ValueError("invalid original MACULA source ID")
    canon = {"n": "nt", "o": "ot"}.get(source_id[0])
    verse = source_id[1:9]
    if canon is None or len(verse) != 8 or not verse.isdigit():
        raise ValueError("invalid original MACULA canon or verse coordinate")
    return canon, verse[:2], verse


def select_cases(index: dict, *, per_stratum: int = 500,
                 seed: str = SEED) -> tuple[list[dict], dict]:
    """Book-diverse, repeatable 4-stratum review cohort; no duplicate verses.

    Guarantee at least one case per nonempty book/stratum when feasible, then
    fill by SHA-256 priority. This deliberately oversamples sparse books and
    is NOT a probability sample for naive whole-corpus error-rate estimates.
    """
    if per_stratum < 1 or not seed:
        raise ValueError("per-stratum count and seed must be positive")
    causes = index["unlinked_cause_by_original_macula_id"]
    if set(causes.values()) != set(STRATA):
        raise ValueError("source cause partition differs from reviewed four strata")
    source_lookup = index["by_original_macula_id"]
    rows = index["rows"]
    groups: dict[str, dict[str, list[str]]] = {
        reason: defaultdict(list) for reason in STRATA
    }
    for source, reason in causes.items():
        canon, book, verse = coordinates(source)
        positions = source_lookup.get(source)
        if not positions or any(not isinstance(i, int) or i < 0 or
                                i >= len(rows) or rows[i]["word_ids"]
                                for i in positions):
            raise ValueError("unresolved source has existing word evidence or invalid index")
        groups[reason][canon + ":" + book].append(source)

    used_verses: set[str] = set()
    selected: list[dict] = []
    population: dict[str, dict] = {}
    for reason in STRATA:
        by_book = groups[reason]
        total = sum(len(ids) for ids in by_book.values())
        if total < per_stratum or len(by_book) > per_stratum:
            raise ValueError("review stratum cannot fulfill book-diverse quota")
        population[reason] = {
            "total": total,
            "by_canon": dict(sorted(Counter(
                key.split(":")[0] for key, ids in by_book.items()
                for _ in ids).items())),
            "books": {k: len(v) for k, v in sorted(by_book.items())},
        }
        chosen: list[str] = []
        # Explicitly cover each represented book; each case comes from a new verse.
        for book in sorted(by_book):
            for source in sorted(by_book[book], key=lambda s: (rank(seed, s), s)):
                verse = coordinates(source)[2]
                if verse not in used_verses:
                    chosen.append(source)
                    used_verses.add(verse)
                    break
            else:
                raise ValueError("unable to preserve book coverage without verse duplication")
        candidates = sorted(
            (source for ids in by_book.values() for source in ids
             if source not in set(chosen)),
            key=lambda s: (rank(seed, s), s))
        for source in candidates:
            if len(chosen) == per_stratum:
                break
            verse = coordinates(source)[2]
            if verse not in used_verses:
                chosen.append(source)
                used_verses.add(verse)
        if len(chosen) != per_stratum:
            raise ValueError("not enough independent verses for exact review quota")
        for source in chosen:
            canon, book, verse = coordinates(source)
            selected.append({
                "case_id": digest(("case:" + seed + ":" + source).encode("utf-8"))[:24],
                "original_macula_id": source,
                "source_cause": reason,
                "canon": canon,
                "book_code": book,
                "source_verse_coordinate": verse,
                "review_status": "unreviewed",
                "manually_approved_french_spans": None,
                "explicit_unpaired_source": None,
                "human_review_evidence": None,
                "machine_candidate_approved": False,
            })

    if len(selected) != len(STRATA) * per_stratum or len(used_verses) != len(selected):
        raise ValueError("sample cardinality or verse isolation changed")
    # Shuffle the exported review order independent of class to avoid a
    # contiguous category reveal; retain category metadata for stratification.
    selected.sort(key=lambda case: (rank(seed + ":presentation", case["original_macula_id"]),
                                    case["original_macula_id"]))
    return selected, population


def render(index: dict, lock: dict, source_sha256: str,
           per_stratum: int = 500) -> tuple[bytes, dict]:
    if source_sha256 != lock["gzip_sha256"]:
        raise ValueError("pinned private MACULA-LSG index checksum mismatch")
    if index["source_clear_bible_revision"] != lock["source_clear_bible_revision"]:
        raise ValueError("Clear.Bible source revision changed")
    if index["source_aquifer_revision"] != lock["source_aquifer_revision"]:
        raise ValueError("Aquifer source revision changed")
    if index["curated_osis_sha256"] != lock["curated_osis_sha256"]:
        raise ValueError("authorial LSG 1.0.2 edition changed")
    expected = lock["unlinked_source_cause_counts"]
    tally = {"nt": Counter(), "ot": Counter()}
    for source, reason in index["unlinked_cause_by_original_macula_id"].items():
        canon, _, _ = coordinates(source)
        tally[canon][reason] += 1
    if any(dict(tally[canon]) != expected[canon] for canon in ("nt", "ot")):
        raise ValueError("unlinked source census disagrees with pinned source")
    cases, population = select_cases(index, per_stratum=per_stratum)
    document = {
        "kind": "brsi-macula-lsg-human-semantic-review-private-unreviewed",
        "schema_version": 1,
        "seed": SEED,
        "source_index_gzip_sha256": source_sha256,
        "case_count": len(cases),
        "reviewed_case_count": 0,
        "automatic_linguistic_approval": False,
        "publication_authorized": False,
        "cases": cases,
    }
    raw = (json.dumps(document, ensure_ascii=False, sort_keys=True,
                      indent=2) + "\n").encode("utf-8")
    report = {
        "kind": "brsi-macula-lsg-stratified-semantic-review-sampling-receipt",
        "schema_version": 1,
        "seed": SEED,
        "source_index_gzip_sha256": source_sha256,
        "source_clear_bible_revision": lock["source_clear_bible_revision"],
        "source_aquifer_revision": lock["source_aquifer_revision"],
        "curated_osis_sha256": lock["curated_osis_sha256"],
        "case_count": len(cases),
        "unique_source_verses": len({case["source_verse_coordinate"] for case in cases}),
        "per_stratum": per_stratum,
        "population": population,
        "sample_by_cause": dict(sorted(Counter(c["source_cause"] for c in cases).items())),
        "sample_by_canon": dict(sorted(Counter(c["canon"] for c in cases).items())),
        "private_unreviewed_cases_sha256": digest(raw),
        "private_unreviewed_cases_bytes": len(raw),
        "book_diversity_priority": True,
        "population_error_rate_estimable_without_weights": False,
        "human_gold_cases": 0,
        "machine_proposals": 0,
        "automatic_linguistic_approval": False,
        "publication_authorized": False,
    }
    return raw, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-index", required=True, type=Path)
    parser.add_argument("--correspondence-lock", required=True, type=Path)
    parser.add_argument("--private-unreviewed-cases", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--per-stratum", type=int, default=500)
    args = parser.parse_args()
    for path in (args.private_unreviewed_cases, args.report):
        if path.resolve().is_relative_to(ROOT):
            raise ValueError("private review outputs must remain outside tracked repository")
    if args.private_unreviewed_cases.resolve() == args.report.resolve():
        raise ValueError("private cases and source-free report must be distinct files")
    lock = json.loads(args.correspondence_lock.read_text(encoding="utf-8"))
    blob = args.original_index.read_bytes()
    source_sha256 = digest(blob)
    if source_sha256 != lock["gzip_sha256"]:
        raise ValueError("original index failed pinned SHA-256 verification")
    index = json.loads(gzip.decompress(blob))
    raw, report = render(index, lock, source_sha256, args.per_stratum)
    args.private_unreviewed_cases.write_bytes(raw)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    # No source IDs, Scripture text or human gold annotations in CI logs.
    print("BRSI_SEMANTIC_REVIEW_SAMPLE_COUNTS",
          report["case_count"], report["sample_by_cause"],
          report["private_unreviewed_cases_sha256"])


if __name__ == "__main__":
    main()
