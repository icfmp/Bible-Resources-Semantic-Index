#!/usr/bin/env python3
"""Inspect only explicit requested verses in frozen Macula source TSVs.

This is a bounded source-witness diagnostic for human adjudication, never
an identity match, automatic record change, or permission to export the
complete Macula annotations.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from pathlib import Path

VERSE = re.compile(r"[0-9]{8}\Z")
COLUMNS = ("xml:id", "text", "lemma", "english", "gloss", "type", "pos")


def inspect(verses: list[str], corpora: dict[str, Path]) -> list[dict]:
    if len(verses) > 40 or len(set(verses)) != len(verses):
        raise ValueError("Source verse inspection limited to 40 distinct verses")
    for verse in verses:
        if not isinstance(verse, str) or not VERSE.fullmatch(verse):
            raise ValueError(f"Invalid ORG verse ID: {verse!r}")
    wanted = set(verses)
    witnesses = {v: [] for v in verses}
    for corpus, path in sorted(corpora.items()):
        if corpus not in {"wlc", "sblgnt"}:
            raise ValueError("Source original-word corpus must be exactly pinned WLC/SBLGNT")
        with path.open(encoding="utf-8-sig", newline="") as input_file:
            reader = csv.DictReader(input_file, delimiter="\t")
            if not set(COLUMNS).issubset(reader.fieldnames or []):
                raise ValueError(f"Missing requested frozen source columns: {path}")
            for row in reader:
                wid = row["xml:id"]
                if len(wid) < 9 or wid[1:9] not in wanted:
                    continue
                verse = wid[1:9]
                if (corpus == "wlc" and not verse.startswith(tuple(f"{i:02d}" for i in range(1,40))) or
                    corpus == "sblgnt" and not verse.startswith(tuple(f"{i:02d}" for i in range(40,67)))):
                    raise ValueError("Original-word verse book outside source corpus")
                witnesses[verse].append({"corpus": corpus, **{c: row[c] for c in COLUMNS}})
    return [{"verse_id": verse, "words": witnesses[verse]} for verse in verses]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wlc", type=Path, required=True)
    parser.add_argument("--sblgnt", type=Path, required=True)
    parser.add_argument("--verses", nargs="+", required=True)
    args = parser.parse_args()
    result = inspect(args.verses, {"wlc": args.wlc, "sblgnt": args.sblgnt})
    for row in result:
        # Source-word IDs and limited short token-level source glosses,
        # never export a full original book, full TSV or annotation corpus.
        print("PINNED_SOURCE_VERSE " + json.dumps(row, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
