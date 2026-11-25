"""Validate identifier-only chapter decisions against exact local source bytes."""
import argparse
import collections
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from reading_text import reading_prose

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
TOKEN = re.compile(r"[^\W\d_]+(?:[’'\-][^\W\d_]+)*")

def require(condition, message):
    if not condition:
        raise ValueError(message)

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def reading_text(data, book, chapter, first, last):
    # Preserve the source's whitespace and punctuation. Exclude OSIS note content.
    # The exact locked reading-text digest fails closed if the source changes.
    text = data.decode("utf-8")
    verses = {}
    for number in range(first, last + 1):
        ref = re.escape(f"{book}.{chapter}.{number}")
        pattern = rf'<verse\b[^>]*\bsID="{ref}"[^>]*/>(.*?)<verse\b[^>]*\beID="{ref}"[^>]*/>'
        matches = re.findall(pattern, text, re.S)
        require(len(matches) == 1, f"Missing or ambiguous OSIS milestone: {ref}")
        verses[number] = reading_prose(matches[0])
    return verses

def validate(ledger, hebrew, french, macula_extra=()):
    sources = ledger["sources"]
    require(git_blob(hebrew) == sources["macula"]["blob"], "MACULA blob mismatch")
    require(git_blob(french) == sources["lsg"]["expected_current_blob"], "LSG blob mismatch")
    scope = re.fullmatch(r"([A-Za-z0-9]+)\.(\d+)\.(\d+)–(\d+)", ledger["scope"])
    require(scope is not None, "Invalid scope")
    book, chapter, first, last = scope.groups()
    first, last = int(first), int(last)
    original = {}
    segments = sources["macula"].get("segments")
    if segments is None:
        require(not macula_extra, "Unexpected supplemental MACULA source")
        segments = [{"blob": sources["macula"]["blob"], "native_chapter": int(chapter),
                     "native_first": first, "native_last": last,
                     "lsg_first": first, "lsg_last": last}]
    require(len(segments) == 1 + len(macula_extra), "MACULA segment count mismatch")
    require(segments[0]["blob"] == sources["macula"]["blob"], "Primary MACULA lock mismatch")
    covered = []
    for segment, data in zip(segments, (hebrew, *macula_extra)):
        require(git_blob(data) == segment["blob"], "MACULA segment blob mismatch")
        nc = segment["native_chapter"]
        nf, nl = segment["native_first"], segment["native_last"]
        lf, ll = segment["lsg_first"], segment["lsg_last"]
        require(1 <= nf <= nl and first <= lf <= ll <= last, "Invalid segment bounds")
        covered.extend(range(lf, ll + 1))
        native_verses = set()
        root = ET.fromstring(data)
        for node in root.iter("w"):
            ref = node.get("ref", "")
            m = re.search(r" (\d+):(\d+)!", ref)
            if m and int(m.group(1)) == nc and nf <= int(m.group(2)) <= nl:
                key = node.get(XML_ID)
                require(key and key not in original, "Invalid/duplicate source identifier")
                original[key] = node.get("pos")
                native_verses.add(int(m.group(2)))
        require(native_verses == set(range(nf, nl + 1)), "Incomplete native segment")
    require(covered == list(range(first, last + 1)), "Target segment inventory mismatch")
    require(bool(original), "No source words")
    prose = reading_text(french, book, chapter, first, last)
    digest = hashlib.sha256("\n".join(prose.values()).encode()).hexdigest()
    require(digest == sources["lsg"]["chapter_prose_sha256"], "LSG chapter reading-text digest mismatch")
    tokens = {(v, i): (m.start(), m.end())
              for v, t in prose.items()
              for i, m in enumerate(TOKEN.finditer(t), 1)}
    h_reverse, f_reverse = collections.defaultdict(set), collections.defaultdict(set)
    seen = set()
    counts = {}
    for i, r in enumerate(ledger["relations"]):
        kind, h, f = r["kind"], r["hebrew"], r["french"]
        require(kind in {"translation", "contextual"}, "Unknown relation kind")
        require(h and f and len(h) == len(set(h)), "Empty or duplicate Hebrew list")
        signature = (kind, tuple(sorted(h)), tuple(sorted(tuple(x) for x in f)))
        require(signature not in seen, "Duplicate relation")
        seen.add(signature)
        for key in h:
            require(key in original, f"Unknown MACULA ID: {key}")
            h_reverse[key].add(i)
        require(len(f) == len({tuple(x) for x in f}), "Duplicate French positions")
        for v, ordinal, start, end in f:
            key = (v, ordinal)
            require(tokens.get(key) == (start, end), f"Invalid French offset: {key}")
            f_reverse[key].add(i)
        for key in h:
            require(i in h_reverse[key], "Hebrew reverse lookup mismatch")
        for v, ordinal, _, _ in f:
            require(i in f_reverse[v, ordinal], "French reverse lookup mismatch")
    require(set(h_reverse) == set(original), "Incomplete Hebrew coverage")
    require(set(f_reverse) == set(tokens), "Incomplete French coverage")
    for kind in ("translation", "contextual"):
        rows = [r for r in ledger["relations"] if r["kind"] == kind]
        counts[kind] = {"relations": len(rows),
                        "hebrew_units": len({h for r in rows for h in r["hebrew"]}),
                        "french_units": len({tuple(f[:2]) for r in rows for f in r["french"]}),
                        "single_original_relations": sum(len(r["hebrew"]) == 1 for r in rows)}
    lexical = {h for h, pos in original.items() if pos in {"noun", "verb", "adjective", "adverb"}}
    translated = {h for r in ledger["relations"] if r["kind"] == "translation" for h in r["hebrew"]}
    actual = {"relations": len(seen), "hebrew_units": len(original), "french_units": len(tokens),
              "lexical_content_units": len(lexical),
              "lexical_content_translation": len(lexical & translated), **counts}
    require(ledger["statistics"] == actual, "Recorded statistics mismatch")
    return actual

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ledger", type=Path)
    p.add_argument("macula", type=Path)
    p.add_argument("lsg", type=Path)
    p.add_argument("--macula-extra", type=Path, action="append", default=[], help="Supplemental MACULA source XML, in declared segment order")
    args = p.parse_args()
    print(json.dumps(validate(json.loads(args.ledger.read_text(encoding="utf-8")),
                              args.macula.read_bytes(), args.lsg.read_bytes(),
                              tuple(p.read_bytes() for p in args.macula_extra)), indent=2))

if __name__ == "__main__":
    main()
