#!/usr/bin/env python3
"""Full source-pinned triage of key verses outside active general references.

Every candidate is preserved; spelling/gloss similarity is research evidence,
never permission to promote an identity, verse, or word automatically.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ("explicit_instances", "pronominal_referents", "subject_referents")
SOURCE_TYPES = ("wlc", "sblgnt")


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def inventory(data: Path) -> list[dict]:
    rows = []
    for path in sorted((data / "entities").glob("*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        labels = record.get("localizations", {}).get("eng", {})
        names = [labels.get("preferred_label", "")]
        names += labels.get("alternate_labels", [])
        names = [x for x in names if isinstance(x, str) and x]
        short_names = set()
        for name in names:
            short_names.add(normalize(name))
            short_names.add(normalize(re.sub(r"\s*\([^()]*\)$", "", name)))
        short_names.discard("")
        direct = {w[1:9] for field in FIELDS[:1]
                  for groups in record.get(field, {}).values()
                  for group in groups for w in group}
        indirect = {w[1:9] for field in FIELDS[1:]
                    for groups in record.get(field, {}).values()
                    for group in groups for w in group}
        for verse in sorted(set(record.get("key_references", [])) -
                            set(record.get("references", []))):
            rows.append({
                "source_id": record["bsi"]["source_id"],
                "path": path.relative_to(data).as_posix(),
                "kind": record["type"],
                "verse_id": verse,
                "names": sorted(short_names),
                "source_direct_word_claim": verse in direct,
                "source_indirect_word_claim": verse in indirect,
            })
    return rows


def get_macula_words(verses: set[str], pinned: dict[str, Path]) -> dict[str, list[dict]]:
    source = defaultdict(list)
    for corpus, path in sorted(pinned.items()):
        if corpus not in SOURCE_TYPES:
            raise ValueError(f"Unexpected original-language corpus: {corpus}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if not {"xml:id", "english", "gloss", "text", "lemma"}.issubset(
                    reader.fieldnames or []
            ):
                raise ValueError(f"Missing exact original columns in pinned {corpus}")
            for record in reader:
                word_id = record["xml:id"]
                if len(word_id) < 9:
                    continue
                verse = word_id[1:9]
                if verse in verses:
                    source[verse].append({
                        "corpus": corpus,
                        "word_id": word_id,
                        "english": record["english"],
                        "gloss": record["gloss"],
                        "lemma": record["lemma"],
                        "text": record["text"],
                    })
    return dict(source)


def review(rows: list[dict], words: dict[str, list[dict]]) -> dict:
    counts = Counter()
    by_kind = defaultdict(Counter)
    cases = []
    for row in rows:
        verse_words = words.get(row["verse_id"], [])
        found = []
        for word in verse_words:
            source_names = {normalize(word[k]) for k in ("english", "gloss")}
            source_names.discard("")
            if not source_names:
                continue
            same = source_names & set(row["names"])
            # A leading possessive/conjunction may be in the source gloss
            # while the entity name is the same; this is a weaker, manual
            # candidate, not an exact known entity.
            fragment = [
                n for n in row["names"] if len(n) >= 4 and
                any(n in s.split() for s in source_names)
            ]
            if not same and not fragment:
                continue
            found.append({
                "word_id": word["word_id"],
                "corpus": word["corpus"],
                "source_english": word["english"],
                "source_gloss": word["gloss"],
                "source_lemma": word["lemma"],
                "source_text": word["text"],
                "match_type": "whole_name_candidate" if same else "partial_name_candidate",
            })
        if row["source_direct_word_claim"]:
            status = "already_direct_source_word_check_integrity"
        elif row["source_indirect_word_claim"]:
            status = "indirect_source_word_not_direct_name"
        elif found:
            status = "unlinked_original_word_name_candidate_review"
        elif int(row["verse_id"][:2]) > 66:
            status = "outside_66_book_source_editions"
        else:
            status = "key_context_or_unresolved_manual_source_review"
        counts[status] += 1
        by_kind[status][row["kind"]] += 1
        cases.append({
            "source_id": row["source_id"],
            "path": row["path"],
            "kind": row["kind"],
            "verse_id": row["verse_id"],
            "status": status,
            "source_word_candidates": found,
        })
    return {
        "schema_version": 1,
        "policy": "candidate_classification_only_not_approved_identity_or_word",
        "counts": dict(sorted(counts.items())),
        "kinds": {k: dict(sorted(v.items())) for k, v in sorted(by_kind.items())},
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--wlc", type=Path, required=True)
    parser.add_argument("--sblgnt", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--max-lines", type=int, default=200)
    args = parser.parse_args()
    cases = inventory(args.data)
    words = get_macula_words({r["verse_id"] for r in cases},
                             {"wlc": args.wlc, "sblgnt": args.sblgnt})
    result = review(cases, words)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print("KEY_SOURCE_AUDIT_COUNTS " + json.dumps({
        "key_only_verse_cases": len(cases),
        "distinct_entities": len({x["source_id"] for x in cases}),
        "counts": result["counts"],
        "kinds": result["kinds"],
    }, sort_keys=True))
    candidates = [r for r in result["cases"]
                  if r["status"] == "unlinked_original_word_name_candidate_review"]
    for candidate in candidates[:args.max_lines]:
        print("KEY_SOURCE_CANDIDATE " + json.dumps(candidate, ensure_ascii=False))
    if len(candidates) > args.max_lines:
        print(f"ADDITIONAL_REVIEW_CANDIDATES {len(candidates) - args.max_lines}")


if __name__ == "__main__":
    main()
