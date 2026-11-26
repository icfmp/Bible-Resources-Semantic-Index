#!/usr/bin/env python3
"""Compact, source-pinned Hebrew/LSG editorial work packets.

Prepare: python scripts/macula_lsg_compact.py prepare Num 30 36
Rebuild: python scripts/macula_lsg_compact.py rebuild Num 30 draft.json
Input draft.json: {"3":"1:2;2:1;3-4:3-5;5~6", ...}.
Each row is keyed by native verse number (same LSG verse by default).
Use {"french_verse": 2, "map": "...", "note": "..."} for verse mapping.
Qualified target ordinals such as 2.4-6 permit cross-verse links.
Colon = lexical correspondence; tilde = contextual attachment.
All ordinals are 1-based. No inference, nearest-token fill or semantic
certification is performed. Unaccounted occurrences remain explicit.
The prepared projection contains text for editorial use; do not publish
source-derived text in distribution ledgers. Rebuilt overlays are drafts.
"""
import argparse
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "links/alignments/macula-lsg/sources"


def read_sources(book, chapter):
    # Explicit native book-code differences; no versification inference.
    native = {
        "Exod": "Exo", "Deut": "Deu", "Josh": "Jos", "Judg": "Jdg",
        "Ruth": "Rut", "Ezra": "Ezr", "Prov": "Pro", "1Sam": "1Sa",
        "2Sam": "2Sa", "1Kgs": "1Ki", "2Kgs": "2Ki", "1Chr": "1Ch",
        "2Chr": "2Ch", "Ps": "Psa", "Eccl": "Ecc", "Song": "Sng",
        "Ezek": "Ezk", "Hos": "HOS", "Joel": "Jol", "Amos": "Amo",
        "Obad": "Oba", "Jonah": "Jon", "Mic": "Mic", "Nah": "Nam",
        "Zeph": "Zep", "Zech": "Zec", "Esth": "Est", "Jer": "Jer",
    }.get(book, book)
    filename = f"{chapter:03d}.json"
    lsg = json.loads((SOURCES / "lsg" / book / filename).read_text(encoding="utf-8"))
    heb = json.loads((SOURCES / "macula-hebrew" / native / filename).read_text(encoding="utf-8"))
    groups = {}
    for word in heb["words"]:
        reference = word[1].split("!")[0]
        v = int(reference.rsplit(":", 1)[1])
        groups.setdefault(v, []).append(word)
    return lsg, heb, groups


def is_word_char(char):
    return unicodedata.category(char)[0] in "LNM"


def french_tokens(text, verse):
    """Unicode code-point offsets; retain internal apostrophes/hyphens."""
    tokens = []
    i = 0
    while i < len(text):
        if not is_word_char(text[i]):
            i += 1
            continue
        start = i
        i += 1
        while i < len(text):
            if is_word_char(text[i]):
                i += 1
            elif text[i] in "'’-" and i + 1 < len(text) and is_word_char(text[i + 1]):
                i += 1
            else:
                break
        tokens.append(([verse, len(tokens) + 1, start, i], text[start:i]))
    return tokens


def ordinal_range(expression):
    start, sep, end = expression.partition("-")
    a, b = int(start), int(end) if sep else int(start)
    if a < 1 or b < a:
        raise ValueError(f"Invalid ordinal range: {expression}")
    return range(a, b + 1)


def resolve_ordinals(expression, values):
    result = []
    for part in expression.split(","):
        for i in ordinal_range(part):
            if i > len(values):
                raise ValueError(f"Ordinal {i} out of range ({len(values)})")
            result.append(values[i - 1])
    if len(set(result)) != len(result):
        raise ValueError(f"Duplicate ordinal: {expression}")
    return result


def target_tuples(expression, default_verse, tokens):
    tuples = []
    for part in expression.split(","):
        if "." in part:
            v, part = part.split(".", 1)
            v = int(v)
        else:
            v = default_verse
        tuples.extend(resolve_ordinals(part, [tuple(t) for t, _ in tokens[v]]))
    if len(set(tuples)) != len(tuples):
        raise ValueError(f"Duplicate French ordinal: {expression}")
    return tuples


def prepare(book, chapter):
    lsg, heb, groups = read_sources(book, chapter)
    yield {"scope": f"{book}.{chapter}", "lsg_sha256": lsg["reading_text_sha256"],
           "macula_blob": heb["git_blob"], "native_verse_count": len(groups)}
    for v in sorted(set(groups) | {int(v) for v in lsg["verses"]}):
        words = groups.get(v, [])
        tokens = french_tokens(lsg["verses"].get(str(v), ""), v)
        yield {"verse": v, "native_reference": words[0][1].split("!")[0] if words else None,
               "hebrew": [[i, w[2], w[3], w[4], w[5]] for i, w in enumerate(words, 1)],
               "french": [[i, t] for i, (_, t) in enumerate(tokens, 1)]}


def rebuild(book, chapter, draft):
    lsg, heb, groups = read_sources(book, chapter)
    tokens = {int(v): french_tokens(t, int(v)) for v, t in lsg["verses"].items()}
    entries = []
    used_h, used_f = set(), set()
    for vs, row in sorted(draft.items(), key=lambda item: int(item[0])):
        v = int(vs)
        row = {"map": row} if isinstance(row, str) else row
        fv = int(row.get("french_verse", v))
        ids = [w[0] for w in groups[v]]
        relations = []
        for relation in row["map"].split(";"):
            relation = relation.strip()
            if not relation:
                continue
            if (":" in relation) == ("~" in relation):
                raise ValueError(f"Invalid relation: {relation}")
            sep = ":" if ":" in relation else "~"
            a, z = relation.split(sep)
            hs = resolve_ordinals(a, ids)
            fs = target_tuples(z, fv, tokens)
            used_h.update(hs)
            used_f.update(fs)
            relations.append({"kind": "translation" if sep == ":" else "contextual",
                              "hebrew": hs, "french": fs,
                              "status": "manual_first_pass_pending_audit"})
        entries.append({"verse": v, "source_reference": groups[v][0][1].split("!")[0],
                        "french_verse": fv, "relations": relations, "note": row.get("note")})
    # Compute coverage after all rows so cross-verse targets are accounted for.
    for entry in entries:
        v, fv = entry["verse"], entry["french_verse"]
        entry["unresolved_hebrew"] = [w[0] for w in groups[v] if w[0] not in used_h]
        entry["unresolved_french"] = [t for t, _ in tokens[fv] if tuple(t) not in used_f]
    return {"scope": f"{book}.{chapter}", "status": "compact_editorial_draft_pending_audit",
            "source_lsg_sha256": lsg["reading_text_sha256"], "source_macula_blob": heb["git_blob"],
            "entries": entries, "compact_map": draft,
            "unprocessed_native_verses": sorted(set(groups) - {int(v) for v in draft}),
            "unresolved_french_chapter": [t for ts in tokens.values() for t, _ in ts
                                          if tuple(t) not in used_f]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("book")
    p.add_argument("chapters", type=int, nargs="+")
    p = sub.add_parser("rebuild")
    p.add_argument("book")
    p.add_argument("chapter", type=int)
    p.add_argument("draft", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        for chapter in args.chapters:
            for record in prepare(args.book, chapter):
                print(json.dumps(record, ensure_ascii=False))
    else:
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        print(json.dumps(rebuild(args.book, args.chapter, draft), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
