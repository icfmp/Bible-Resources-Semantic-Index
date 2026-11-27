#!/usr/bin/env python3
"""Source-pinned Hebrew/LSG cohort production; never performs editorial review.

See docs/MACULA_LSG_COHORT_METHOD.md. Local packets may contain source text.
Only identifier/ordinal decisions and provenance belong in Git.
"""
import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from macula_lsg_compact import (ROOT, SOURCES, french_tokens, source_paths,
                               resolve_ordinals, target_tuples)

LEXICAL = {"noun", "verb", "adjective", "adverb"}
SCHEMA = 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=strict_pairs,
                      parse_constant=lambda x: require(False, f"Invalid JSON: {x}"))


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(dump(value).encode("utf-8")).hexdigest()


def blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def write(path, value):
    path = Path(path)
    require(not path.exists(), f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(dump(value) + "\n")


def split_scope(scope):
    m = re.fullmatch(r"([A-Za-z0-9]+)\.([1-9]\d*)", scope)
    require(m, f"Invalid chapter scope: {scope}")
    return m[1], int(m[2])


def split_ref(ref):
    scope, _, v = ref.rpartition(".")
    split_scope(scope)
    require(re.fullmatch(r"[1-9]\d*", v), f"Invalid verse reference: {ref}")
    return scope, int(v)


def expand_scopes(specs):
    result = []
    for spec in specs:
        m = re.fullmatch(r"([A-Za-z0-9]+)\.([1-9]\d*)(?:-([1-9]\d*))?", spec)
        require(m, f"Invalid scope range: {spec}")
        first, last = int(m[2]), int(m[3] or m[2])
        require(first <= last, f"Reversed scope range: {spec}")
        result.extend(f"{m[1]}.{c}" for c in range(first, last + 1))
    require(result and len(result) == len(set(result)), "Empty or duplicate scopes")
    return result


class VerseTokens(list):
    def __init__(self, text, verse):
        super().__init__(french_tokens(text, verse))
        self.text = text


def corpus(chapters, native_chapters):
    french, native, pins, ids = {}, {}, {"lsg": {}, "macula": {}}, set()
    for scope in chapters:
        book, chapter = split_scope(scope)
        path, _ = source_paths(book, chapter)
        data = read(path)
        require(data["book"] == book and data["chapter"] == chapter,
                f"Wrong LSG projection: {scope}")
        verses = {int(v): t for v, t in data["verses"].items()}
        require(verses and all(v > 0 for v in verses), f"Empty LSG: {scope}")
        text_sha = hashlib.sha256("\n".join(verses[v] for v in sorted(verses)).encode()).hexdigest()
        require(text_sha == data["reading_text_sha256"], f"LSG reading-text hash mismatch: {scope}")
        french[scope] = {v: VerseTokens(t, v) for v, t in sorted(verses.items())}
        pins["lsg"][scope] = {"projection_blob": blob(path), "reading_text_sha256": text_sha}
    for scope in native_chapters:
        book, chapter = split_scope(scope)
        _, path = source_paths(book, chapter)
        data = read(path)
        groups = defaultdict(list)
        for word in data["words"]:
            require(len(word) == 7 and word[0] and word[0] not in ids,
                    f"Invalid/duplicate MACULA ID: {word[0]}")
            ids.add(word[0])
            m = re.search(r" (\d+):(\d+)!", word[1])
            require(m and int(m[1]) == chapter, f"Invalid native reference: {word[1]}")
            groups[int(m[2])].append(word)
        require(groups, f"Empty native projection: {scope}")
        for v, words in sorted(groups.items()):
            native[f"{scope}.{v}"] = words
        pins["macula"][scope] = {"projection_blob": blob(path),
                                  "upstream_blob": data["git_blob"],
                                  "upstream_path": data["source_path"]}
    for key, dirname in (("lsg_manifest", "lsg"), ("macula_manifest", "macula-hebrew")):
        pins[key] = blob(SOURCES / dirname / "manifest.json")
    return french, native, pins


def route_inventory(french, native, routes, identity_default):
    require(set(routes) <= set(native), "Unknown native route")
    targets = {}
    for ref in native:
        target = routes.get(ref, ref if identity_default else None)
        require(target is not None, f"Explicit route required: {ref}")
        scope, v = split_ref(target)
        require(scope in french and v in french[scope], f"Target missing: {ref} -> {target}")
        require(split_ref(ref)[0].split(".")[0] == scope.split(".")[0],
                f"Cross-book route not supported: {ref}")
        targets[ref] = target
    expected = {f"{s}.{v}" for s, verses in french.items() for v in verses}
    require(set(targets.values()) == expected,
            "Target verse inventory not fully covered; explicit source-gap handling required")
    return targets


def make_plan(chapters, routing):
    native_chapters = routing.get("native_chapters", chapters)
    require(native_chapters and len(native_chapters) == len(set(native_chapters)),
            "Empty or duplicate native chapter scope")
    french, native, pins = corpus(chapters, native_chapters)
    targets = route_inventory(french, native, routing.get("routes", {}),
                              routing.get("identity_default") is True)
    return {"schema_version": SCHEMA, "language": "hebrew", "chapters": chapters,
            "native_chapters": native_chapters, "source_pins": pins,
            "targets": targets, "status": "prepared_not_aligned"}


def load_plan(path):
    plan = read(path)
    require(plan["schema_version"] == SCHEMA and plan["language"] == "hebrew",
            "Unsupported plan")
    require(len(plan["chapters"]) == len(set(plan["chapters"])) and
            len(plan["native_chapters"]) == len(set(plan["native_chapters"])),
            "Duplicate plan scopes")
    french, native, pins = corpus(plan["chapters"], plan["native_chapters"])
    require(pins == plan["source_pins"], "Pinned projection or manifest changed")
    targets = route_inventory(french, native, plan["targets"], False)
    return plan, french, native, targets


def norm(s):
    return unicodedata.normalize("NFC", re.sub(r"[\u0591-\u05af]", "",
                                             unicodedata.normalize("NFD", s)))


def bank_index(path):
    index = defaultdict(list)
    if path:
        for i, e in enumerate(read(path)["entries"], 1):
            # The bank stores JSON-encoded tuples, not a second source of text.
            keys = [tuple(json.loads(x)) for x in e["h"]]
            index[keys[0]].append((i, keys, e["f"]))
    return index


def ordinal_text(start, count):
    return str(start + 1) if count == 1 else f"{start + 1}-{start + count}"


def proposals(words, tokens, index):
    keys = [(norm(w[2]), *w[3:7]) for w in words]
    surfaces = [s.lower() for _, s in tokens]
    for i, key in enumerate(keys):
        for number, h, f in index.get(key, []):
            if keys[i:i+len(h)] != h:
                continue
            hl = [j for j in range(len(keys)) if keys[j:j+len(h)] == h]
            fl = [j for j in range(len(surfaces)) if surfaces[j:j+len(f)] == f]
            if len(hl) == len(fl) == 1:
                yield [f"{ordinal_text(i, len(h))}:{ordinal_text(fl[0], len(f))}", number]


def select_refs(native, scopes):
    if not scopes:
        return list(native)
    selected = set(expand_scopes(scopes))
    require(selected <= {split_ref(r)[0] for r in native}, "Unknown selected scope")
    return [r for r in native if split_ref(r)[0] in selected]


def normalize_row(value):
    row = {"map": value} if isinstance(value, str) else value
    require(isinstance(row, dict) and set(row) <= {"map", "note", "omissions"} and
            isinstance(row.get("map"), str), "Invalid decision row")
    if "note" in row:
        require(isinstance(row["note"], str), "Invalid note")
    return row


def decode(ref, row, french, native, targets):
    row = normalize_row(row)
    scope, v = split_ref(targets[ref])
    words = native[ref]
    ids = [w[0] for w in words]
    relations, seen = [], set()
    for relation in row["map"].split(";"):
        relation = relation.strip()
        if not relation:
            continue
        require((relation.count(":") == 1 and "~" not in relation) or
                (relation.count("~") == 1 and ":" not in relation),
                f"{ref}: invalid relation {relation}")
        sep = ":" if ":" in relation else "~"
        a, b = relation.split(sep)
        h = resolve_ordinals(a, ids)
        f = target_tuples(b, v, french[scope])
        kind = "translation" if sep == ":" else "contextual"
        signature = (kind, tuple(sorted(h)), tuple(sorted(f)))
        require(signature not in seen, f"{ref}: duplicate relation")
        seen.add(signature)
        relations.append({"kind": kind, "hebrew": h, "french": [list(x) for x in f]})
    used = {h for rel in relations for h in rel["hebrew"]}
    omissions, omitted = [], set()
    for item in row.get("omissions", []):
        require(set(item) == {"ordinals", "note"} and isinstance(item["note"], str) and
                item["note"].strip(), f"{ref}: omission requires evidence")
        h = resolve_ordinals(item["ordinals"], ids)
        require(not (set(h) & (used | omitted)), f"{ref}: overlapping omission")
        omitted.update(h)
        omissions.append({"hebrew": h, "reason": "omitted_in_target", "note": item["note"]})
    return relations, omissions, set(ids) - used - omitted


def draft_envelope(plan, rows):
    return {"schema_version": SCHEMA, "plan_sha256": digest(plan),
            "status": "manual_first_pass_pending_audit", "rows": rows}


def load_draft(path, plan, french, native, targets):
    draft = read(path)
    require(draft["schema_version"] == SCHEMA and draft["plan_sha256"] == digest(plan),
            "Draft belongs to a different plan")
    require(set(draft["rows"]) <= set(native), "Unexpected draft references")
    for ref, row in draft["rows"].items():
        decode(ref, row, french, native, targets)
    return draft


def legacy_rows(paths, plan, native, targets):
    rows = {}
    for path in paths:
        data = read(path)
        for c in data["chapters"]:
            scope = c["scope"]
            require(scope in plan["source_pins"]["macula"], f"Out-of-plan legacy chapter: {scope}")
            hp = plan["source_pins"]["macula"][scope]
            for verse, row in c["rows"].items():
                if "manual_map" not in row:
                    continue
                ref = f"{scope}.{verse}"
                target = row["french_target"]
                require(ref in native and target == targets[ref], f"Legacy route mismatch: {ref}")
                fp = plan["source_pins"]["lsg"][split_ref(target)[0]]
                require(c["source_lsg_projection_blob"] == fp["projection_blob"] and
                        c["source_lsg_sha256"] == fp["reading_text_sha256"] and
                        c["source_macula_projection_blob"] == hp["projection_blob"] and
                        c["source_macula_blob"] == hp["upstream_blob"],
                        f"Legacy source mismatch: {ref}")
                require(ref not in rows, f"Duplicate legacy row: {ref}")
                decision = {"map": row["manual_map"]}
                if row.get("note"):
                    decision["note"] = row["note"]
                # Historical uncovered ordinals are not automatically accepted as omissions.
                rows[ref] = decision
    return rows


def review_overlay(plan, draft, paths, french, native, targets):
    effective = dict(draft["rows"])
    reviewed, changed = set(), set()
    notes = {}
    for path in paths:
        delta = read(path)
        require(delta["schema_version"] == SCHEMA and
                delta["plan_sha256"] == digest(plan) and
                delta["draft_sha256"] == digest(draft), "Review is not bound to this draft")
        batch = delta["reviewed"]
        require(isinstance(batch, list) and len(batch) == len(set(batch)) and
                set(batch) <= set(draft["rows"]), "Unknown reviewed reference")
        corrections = delta.get("corrections", {})
        if "amends_effective_sha256" in delta:
            require(delta["amends_effective_sha256"] == digest(effective) and
                    set(batch) <= reviewed and set(corrections) == set(batch),
                    "Amendments require an exact preceding effective digest and explicit corrections")
        else:
            require(not reviewed.intersection(batch), "Repeated reviewed reference")
        require(set(corrections) <= set(batch), "Correction without explicit review")
        for ref, value in corrections.items():
            previous = normalize_row(effective[ref])
            update = normalize_row(value)
            # Map-only corrections retain the existing note/omission evidence.
            replacement = {**previous, **update}
            require(replacement != previous, f"No-op correction: {ref}")
            decode(ref, replacement, french, native, targets)
            effective[ref] = replacement
            changed.add(ref)
        new_notes = delta.get("notes", {})
        require(set(new_notes) <= set(batch) and
                all(isinstance(n, str) and n.strip() for n in new_notes.values()),
                "Invalid review notes")
        notes.update(new_notes)
        reviewed.update(batch)
    return effective, reviewed, changed, notes


def summary(plan, draft, effective, reviewed, changed, french, native, targets):
    reports, ledgers = {}, {}
    lm, hm = read(SOURCES / "lsg" / "manifest.json"), read(SOURCES / "macula-hebrew" / "manifest.json")
    by_target = defaultdict(list)
    for ref, target in targets.items():
        by_target[split_ref(target)[0]].append(ref)
    for scope in plan["chapters"]:
        refs = by_target[scope]
        words = {w[0]: w[4] for ref in refs for w in native[ref]}
        all_f = {tuple(t) for ts in french[scope].values() for t, _ in ts}
        relations, omissions = [], []
        for ref in refs:
            if ref in effective:
                rr, oo, _ = decode(ref, effective[ref], french, native, targets)
                relations.extend(rr)
                omissions.extend(oo)
        signatures = {(r["kind"], tuple(sorted(r["hebrew"])), tuple(sorted(map(tuple, r["french"]))))
                      for r in relations}
        require(len(signatures) == len(relations), f"Duplicate chapter relation: {scope}")
        reverse_h, reverse_f = defaultdict(set), defaultdict(set)
        for i, rel in enumerate(relations):
            for h in rel["hebrew"]:
                require(h in words, f"Unknown native ID: {h}")
                reverse_h[h].add(i)
            for f in map(tuple, rel["french"]):
                require(f in all_f, f"Unknown French offset: {f}")
                reverse_f[f].add(i)
        omitted = {h for o in omissions for h in o["hebrew"]}
        require(not omitted.intersection(reverse_h), "Omission overlaps a relation")
        for h, ii in reverse_h.items():
            require(all(h in relations[i]["hebrew"] for i in ii), "Reverse native mismatch")
        for f, ii in reverse_f.items():
            require(all(list(f) in relations[i]["french"] for i in ii), "Reverse French mismatch")
        missing_h = sorted(set(words) - set(reverse_h) - omitted)
        missing_f = sorted(all_f - set(reverse_f))
        lexical = {h for h, pos in words.items() if pos in LEXICAL}
        translated = {h for r in relations if r["kind"] == "translation" for h in r["hebrew"]}
        stats = {"relations": len(relations), "hebrew_units": len(words),
                 "french_units": len(all_f), "lexical_content_units": len(lexical),
                 "lexical_content_translation": len(lexical & translated)}
        for kind in ("translation", "contextual"):
            rr = [r for r in relations if r["kind"] == kind]
            stats[kind] = {"relations": len(rr),
                           "hebrew_units": len({h for r in rr for h in r["hebrew"]}),
                           "french_units": len({tuple(f[:2]) for r in rr for f in r["french"]}),
                           "single_original_relations": sum(len(r["hebrew"]) == 1 for r in rr)}
        coverage = len(lexical & translated) / len(lexical) if lexical else None
        complete = set(refs) <= reviewed and not missing_h and not missing_f
        eligible = complete and coverage is not None and 100 * len(lexical & translated) >= 95 * len(lexical)
        reports[scope] = {"native_verses": len(refs), "drafted": sum(r in effective for r in refs),
                          "reviewed": sum(r in reviewed for r in refs), "changed": sum(r in changed for r in refs),
                          "statistics": stats, "lexical_coverage": coverage,
                          "unaccounted_hebrew": missing_h, "unaccounted_french": missing_f,
                          "explicit_omissions": len(omitted), "eligible_for_editorial_acceptance": eligible}
        if not eligible:
            continue
        segments = []
        for ref in sorted(refs, key=lambda x: (split_ref(targets[x])[1], plan["native_chapters"].index(split_ref(x)[0]), split_ref(x)[1])):
            ns, nv = split_ref(ref)
            _, nc = split_scope(ns)
            _, fv = split_ref(targets[ref])
            pin = plan["source_pins"]["macula"][ns]
            seg = {"blob": pin["upstream_blob"], "native_chapter": nc,
                   "native_first": nv, "native_last": nv, "lsg_first": fv, "lsg_last": fv}
            if segments and segments[-1]["blob"] == seg["blob"] and segments[-1]["native_chapter"] == nc and segments[-1]["native_last"]+1 == nv and segments[-1]["lsg_last"]+1 == fv:
                segments[-1]["native_last"] = nv
                segments[-1]["lsg_last"] = fv
            else:
                segments.append(seg)
        primary = plan["source_pins"]["macula"][next(s for s in plan["native_chapters"] if plan["source_pins"]["macula"][s]["upstream_blob"] == segments[0]["blob"])]
        verses = sorted(french[scope])
        require(verses == list(range(verses[0], verses[-1]+1)), "Noncontiguous LSG inventory")
        ledger = {"schema_version": 1, "scope": f"{scope}.{verses[0]}–{verses[-1]}",
                  "status": "recorded same-editor passes; projection checks only; editorial acceptance and publication validation pending",
                  "attribution": hm["attribution"] + " LSG: " + lm["license"],
                  "sources": {"macula": {"commit": hm["commit"], "path": primary["upstream_path"],
                                         "blob": primary["upstream_blob"], "segments": segments},
                              "lsg": {"snapshot": "Pinned LSG working corpus",
                                      "chapter_prose_sha256": plan["source_pins"]["lsg"][scope]["reading_text_sha256"],
                                      "expected_current_blob": lm["git_blob"], "expected_commit": lm["commit"],
                                      "expected_current_size": lm["bytes"],
                                      "verification": "Committed projection only; exact upstream OSIS validation pending."}},
                  "french_tuple": "[verse, 1-based token ordinal, Unicode code-point start, exclusive end]",
                  "relation_kinds": {"translation": "translation correspondence, not a certified dictionary sense",
                                     "contextual": "grammatical/discourse attachment only"},
                  "statistics": stats, "relations": relations}
        if omissions:
            ledger["omissions"] = omissions
        ledgers[scope] = ledger
    return {"schema_version": SCHEMA, "plan_sha256": digest(plan), "draft_sha256": digest(draft),
            "status": "projection_checks_only_not_independent_audit_or_publication",
            "chapters": reports, "native_verses": len(native), "drafted": len(draft["rows"]),
            "reviewed": len(reviewed), "corrected": len(changed),
            "eligible_chapters": len(ledgers), "remaining_first_pass": [r for r in native if r not in draft["rows"]],
            "remaining_review": [r for r in native if r not in reviewed]}, ledgers


def packet(ref, french, native, targets, row=None, index=None, pairs=False):
    scope, v = split_ref(targets[ref])
    words, tokens = native[ref], french[scope][v]
    h = " ".join(f"{i}{w[2] or '∅'}" + (f"/{w[3]}" if norm(w[2]) != norm(w[3]) else "")
                 for i, w in enumerate(words, 1))
    if isinstance(tokens, VerseTokens):
        pieces, offset = [], 0
        for i, ((_, _, start, end), surface) in enumerate(tokens, 1):
            pieces.extend([tokens.text[offset:start], str(i), surface])
            offset = end
        pieces.append(tokens.text[offset:])
        f = "".join(pieces)
    else:
        f = " ".join(f"{i}{s}" for i, (_, s) in enumerate(tokens, 1))
    line = f"{ref}" + (f"->{targets[ref]}" if ref != targets[ref] else "") + f" | H {h} | F {f}"
    if row is not None:
        row = normalize_row(row)
        line += " | A " + row["map"]
        if row.get("omissions"):
            line += " | O " + dump(row["omissions"])
        if pairs:
            rr, _, _ = decode(ref, row, french, native, targets)
            hs = {w[0]: w[2] or "∅" for w in words}
            fs = {tuple(t): s for ts in french[scope].values() for t, s in ts}
            line += " | P " + ";".join(" ".join(hs[h] for h in r["hebrew"]) +
                       (":" if r["kind"] == "translation" else "~") +
                       " ".join(fs[tuple(f)] for f in r["french"]) for r in rr)
    elif index:
        line += " | C? " + " ".join(f"{p}@{i}" for p, i in proposals(words, tokens, index))
    return line


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("scopes", nargs="+")
    p.add_argument("--out", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--confirm-identity", action="store_true")
    g.add_argument("--routing")
    for cmd in ("prepare", "draft", "audit", "review-template", "report", "finalize"):
        p = sub.add_parser(cmd)
        p.add_argument("plan")
        if cmd in {"prepare", "audit"}:
            p.add_argument("--scopes", nargs="+")
            p.add_argument("--draft", required=cmd == "audit")
            p.add_argument("--skip-reviewed", action="store_true")
            p.add_argument("--review", action="append", default=[])
            p.add_argument("--pairs", action="store_true")
            p.add_argument("--bank")
        elif cmd == "draft":
            p.add_argument("--base")
            p.add_argument("--legacy", action="append", default=[])
            p.add_argument("--decisions", action="append", default=[])
            p.add_argument("--out", required=True)
        else:
            p.add_argument("draft")
            if cmd == "review-template":
                p.add_argument("--out", required=True)
            else:
                p.add_argument("--review", action="append", default=[])
                if cmd == "finalize":
                    p.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.cmd == "plan":
        routing = read(args.routing) if args.routing else {"identity_default": True}
        write(args.out, make_plan(expand_scopes(args.scopes), routing))
        return
    plan, french, native, targets = load_plan(args.plan)
    if args.cmd == "draft":
        rows = dict(load_draft(args.base, plan, french, native, targets)["rows"]) if args.base else {}
        for ref, row in legacy_rows(args.legacy, plan, native, targets).items():
            require(ref not in rows, f"Duplicate imported decision: {ref}")
            rows[ref] = row
        for path in args.decisions:
            for ref, row in read(path).items():
                require(ref not in rows, f"Refusing to overwrite first-pass decision: {ref}")
                rows[ref] = normalize_row(row)
        require(set(rows) <= set(native), "Out-of-plan draft references")
        for ref, row in rows.items():
            decode(ref, row, french, native, targets)
        write(args.out, draft_envelope(plan, rows))
        return
    draft = load_draft(args.draft, plan, french, native, targets) if args.draft else draft_envelope(plan, {})
    if args.cmd == "review-template":
        require(set(draft["rows"]) == set(native), "Finish the entire first pass before review")
        write(args.out, {"schema_version": SCHEMA, "plan_sha256": digest(plan),
                         "draft_sha256": digest(draft), "reviewed": [], "corrections": {}, "notes": {}})
        return
    if args.cmd in {"audit", "finalize"} or args.review:
        require(set(draft["rows"]) == set(native), "Finish the entire first pass before review")
    effective, reviewed, changed, notes = review_overlay(plan, draft, args.review, french, native, targets)
    if args.cmd in {"prepare", "audit"}:
        index = bank_index(args.bank)
        print("# plan=" + digest(plan) + " draft=" + digest(draft) +
              (" bank_blob=" + blob(args.bank) if args.bank else ""))
        for ref in select_refs(native, args.scopes):
            if args.cmd == "prepare" and ref in draft["rows"]:
                continue
            if args.skip_reviewed and ref in reviewed:
                continue
            print(packet(ref, french, native, targets,
                         effective.get(ref) if args.cmd == "audit" else None, index, args.pairs))
        return
    report, ledgers = summary(plan, draft, effective, reviewed, changed, french, native, targets)
    report["review_sha256"] = [digest(read(p)) for p in args.review]
    report["effective_sha256"] = digest(effective)
    if args.cmd == "report":
        print(dump(report))
        return
    require(report["eligible_chapters"] == len(plan["chapters"]),
            "Cohort not eligible; inspect report for remaining work or coverage failures")
    out = Path(args.out)
    require(not out.exists(), "Use a fresh output directory")
    out.mkdir(parents=True)
    write(out / "report.json", report)
    write(out / "effective-maps.json", {"plan_sha256": digest(plan), "draft_sha256": digest(draft),
                                      "review_sha256": report["review_sha256"],
                                      "effective_sha256": report["effective_sha256"],
                                      "reviewed": sorted(reviewed), "corrections": sorted(changed),
                                      "rows": effective, "notes": notes})
    for scope, ledger in ledgers.items():
        write(out / (scope + ".json"), ledger)


if __name__ == "__main__":
    main()
