#!/usr/bin/env python3
"""Read-only edition comparison: pinned Clear.Bible LSG target TSV vs curated OSIS.

No source words, translation words, target remaps, public assets or publication.
An alphanumeric verse match is evidence about surface content only; it is NOT
tokenization/word-link certification or a license for guessed alignment IDs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
import xml.sax
from collections import Counter, defaultdict
from pathlib import Path

OSIS_BOOKS = (
    "Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs "
    "1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek "
    "Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal "
    "Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col "
    "1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet "
    "1John 2John 3John Jude Rev"
).split()
BOOK_NUMBERS = {name: i + 1 for i, name in enumerate(OSIS_BOOKS)}
BCV_RE = re.compile(r"^[0-9]{8}$")
TARGET_RE = re.compile(r"^[0-9]{11,12}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
EXCLUDED = {"note", "title", "header", "figure"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pinned_file(root: Path, rel: str, expected: str) -> Path:
    relative = Path(rel)
    if relative.is_absolute() or ".." in relative.parts or not SHA_RE.fullmatch(expected):
        raise ValueError("unsafe file path or invalid SHA-256 source pin")
    file = root / relative
    if sha256(file) != expected:
        raise ValueError(f"pinned byte witness differs: {rel}")
    return file


def osis_bcv(ref: str) -> str:
    parts = ref.split(".")
    if len(parts) != 3 or parts[0] not in BOOK_NUMBERS:
        raise ValueError(f"unsupported OSIS verse coordinate {ref!r}")
    try:
        chapter, verse = int(parts[1]), int(parts[2])
    except ValueError as exc:
        raise ValueError(f"invalid OSIS chapter or verse {ref!r}") from exc
    if not 1 <= chapter <= 150 or not 1 <= verse <= 176:
        raise ValueError(f"OSIS coordinate out of numeric range {ref!r}")
    return f"{BOOK_NUMBERS[parts[0]]:02d}{chapter:03d}{verse:03d}"


class VerseReader(xml.sax.handler.ContentHandler):
    """Extract only authored verse-body character data, excluding notes/titles."""

    def __init__(self):
        super().__init__()
        self.verses: dict[str, list[str]] = {}
        self.active: str | None = None
        self.embedded = False
        self.excluded_depth = 0
        self.verse_start_count = 0

    def startElement(self, name, attrs):
        tag = name.rsplit(":", 1)[-1]
        if tag in EXCLUDED:
            self.excluded_depth += 1
        if tag == "verse":
            closing = attrs.get("eID")
            opening = attrs.get("sID") or attrs.get("osisID")
            if closing:
                if self.active != osis_bcv(closing):
                    raise ValueError(f"verse close coordinate does not match start {closing!r}")
                self.active = None
                self.embedded = False
            elif opening:
                if self.active is not None:
                    raise ValueError("nested or unterminated OSIS verse")
                key = osis_bcv(opening)
                if key in self.verses:
                    raise ValueError(f"duplicate source-authored OSIS verse {opening!r}")
                self.active = key
                self.verses[key] = []
                self.embedded = "sID" not in attrs
                self.verse_start_count += 1
            else:
                raise ValueError("verse with neither start nor end coordinate")
        elif tag in ("p", "lb", "l", "divineName") and self.active and not self.excluded_depth:
            self.verses[self.active].append(" ")

    def endElement(self, name):
        tag = name.rsplit(":", 1)[-1]
        if tag == "verse" and self.embedded:
            self.active = None
            self.embedded = False
        if tag in EXCLUDED:
            self.excluded_depth -= 1
            if self.excluded_depth < 0:
                raise ValueError("unbalanced exclusions")

    def characters(self, content):
        if self.active is not None and self.excluded_depth == 0:
            self.verses[self.active].append(content)


def read_osis(path: Path) -> dict[str, str]:
    collector = VerseReader()
    xml.sax.parse(str(path), collector)
    if collector.active or collector.excluded_depth:
        raise ValueError("unterminated OSIS verse or exclusion")
    if collector.verse_start_count != len(collector.verses) or not collector.verses:
        raise ValueError("invalid or empty OSIS verse census")
    return {key: "".join(parts) for key, parts in collector.verses.items()}


def readable(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def character_stream(text: str) -> str:
    """Conservative punctuation/case-insensitive Unicode comparison, NOT exact text."""
    return "".join(c for c in unicodedata.normalize("NFC", text).casefold() if c.isalnum())


def word_stream(text: str) -> list[str]:
    """Diagnostic whitespace/punctuation tokenization; never an ID mapping."""
    return [character_stream(word) for word in
            re.findall(r"[^\W_]+(?:['’\-][^\W_]+)*", unicodedata.normalize("NFC", text))
            if character_stream(word)]


def read_target_tsv(path: Path, field: str = "text") -> tuple[dict[str, list[str]], dict[str, int]]:
    """Retain the exact TSV ordinal order and token surfaces, without inferred IDs."""
    tokens: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = reader.fieldnames or []
        idfield = "id" if "id" in columns else "identifier" if "identifier" in columns else None
        if idfield is None or field not in columns:
            raise ValueError(f"original target TSV requires ID and {field!r} columns; found {columns!r}")
        total = blank = 0
        for row in reader:
            tid = row[idfield]
            if not isinstance(tid, str) or not TARGET_RE.fullmatch(tid) or tid in seen:
                raise ValueError("invalid or duplicate original target selector")
            seen.add(tid)
            if row.get(field) is None:
                raise ValueError("missing target text column value")
            text = row[field]
            if not text.strip():
                blank += 1
            total += 1
            tokens[tid[:8]].append((int(tid[8:11]), int(tid[11:]) if len(tid) == 12 else 0, tid, text))
    result = {}
    for verse, entries in tokens.items():
        sorted_entries = sorted(entries, key=lambda p: (p[0], p[1]))
        if len({(x[0], x[1]) for x in sorted_entries}) != len(sorted_entries):
            raise ValueError("conflicting target token ordinals in one verse")
        result[verse] = [(identifier, text) for _, _, identifier, text in sorted_entries]
    return result, {"token_rows": total, "blank_token_surfaces": blank, "distinct_verses": len(result)}


def _nt_token_boundaries(source_text: str, targets: list[tuple[str, str]]):
    """Compare only surface character spans; do not create word/ID links."""
    words = word_stream(source_text)
    boundaries = {0: 0}
    cumulative = 0
    for i, word in enumerate(words, 1):
        cumulative += len(word)
        boundaries[cumulative] = i
    result = {}
    offset = 0
    for identifier, word in targets:
        surface = character_stream(word)
        end = offset + len(surface)
        if not surface:
            status = "punctuation_only"
        elif offset in boundaries and end in boundaries:
            count = boundaries[end] - boundaries[offset]
            status = "whole_one_word" if count == 1 else "whole_multiple_words"
        else:
            status = "splits_curated_word_boundary"
        result[identifier] = status
        offset = end
    if offset != cumulative:
        raise ValueError("attempted span mapping across nonidentical character streams")
    return result


def compare_nt(osis_verses: dict[str, str], targets: dict[str, list[tuple[str, str]]],
               census: dict[str, int], nt_candidate: dict):
    source = {k: v for k, v in osis_verses.items() if int(k[:2]) >= 40}
    by_book: dict[str, Counter] = defaultdict(Counter)
    kinds = Counter()
    diagnostic_word_order_equal = 0
    surface_boundaries = Counter()
    aligned_boundaries = Counter()
    aligned_by_book: dict[str, Counter] = defaultdict(Counter)
    mismatching_verses = []
    if (nt_candidate.get("canon") != "nt" or
            nt_candidate.get("format") != "brsi-translation-alignment-candidate"):
        raise ValueError("not the original NT alignment candidate format")
    if nt_candidate.get("coverage", {}).get("records") != len(nt_candidate.get("records", [])):
        raise ValueError("NT alignment record census inconsistent")
    aligned_target_ids = set()
    for record in nt_candidate["records"]:
        for token in record.get("target_lookup_ids", []):
            if not isinstance(token, str) or not TARGET_RE.fullmatch(token):
                raise ValueError("invalid aligned NT target ID")
            aligned_target_ids.add(token)
    observed_aligned_ids = set()
    for key in sorted(set(source) | set(targets)):
        if key not in source:
            status = "target_only_verse"
        elif key not in targets:
            status = "curated_only_verse"
        else:
            target_text = " ".join(text for _, text in targets[key])
            source_text = source[key]
            if readable(target_text) == readable(source_text):
                status = "exact_nfc_whitespace_verse"
            elif character_stream(target_text) == character_stream(source_text):
                status = "same_alphanumeric_stream"
            else:
                status = "different_alphanumeric_stream"
            if word_stream(target_text) == word_stream(source_text):
                diagnostic_word_order_equal += 1
            if status != "different_alphanumeric_stream":
                classified = _nt_token_boundaries(source_text, targets[key])
                for identifier, category in classified.items():
                    surface_boundaries[category] += 1
                    if identifier in aligned_target_ids:
                        observed_aligned_ids.add(identifier)
                        aligned_boundaries[category] += 1
                        aligned_by_book[key[:2]][category] += 1
            else:
                mismatching_verses.append({
                    "bcv": key,
                    "curated_alphanumeric_characters": len(character_stream(source_text)),
                    "target_alphanumeric_characters": len(character_stream(target_text)),
                })
                for identifier, _ in targets[key]:
                    surface_boundaries["verse_text_mismatch"] += 1
                    if identifier in aligned_target_ids:
                        observed_aligned_ids.add(identifier)
                        aligned_boundaries["verse_text_mismatch"] += 1
                        aligned_by_book[key[:2]]["verse_text_mismatch"] += 1
        kinds[status] += 1
        by_book[key[:2]][status] += 1
    if sum(kinds.values()) != len(set(source) | set(targets)):
        raise ValueError("inconsistent NT verse universe")
    if sum(surface_boundaries.values()) > census["token_rows"]:
        raise ValueError("classified more target IDs than source TSV contains")
    if sum(aligned_boundaries.values()) != len(observed_aligned_ids):
        raise ValueError("aligned boundary census inconsistent")
    target_inventory_ids = {identifier for rows in targets.values() for identifier, _ in rows}
    missing_aligned = aligned_target_ids - target_inventory_ids
    if len(missing_aligned) != nt_candidate["coverage"].get("problem_target_token_unattested", 0):
        raise ValueError("unattested target count differs from original candidate")
    return {
        "curated_nt_verses": len(source),
        "clear_bible_target_nt_verses": len(targets),
        **census,
        "verse_content_comparison": dict(sorted(kinds.items())),
        "diagnostic_word_streams_equal_verses": diagnostic_word_order_equal,
        "target_surface_boundary_classes": dict(sorted(surface_boundaries.items())),
        "aligned_attested_target_boundary_classes": dict(sorted(aligned_boundaries.items())),
        "aligned_attested_target_by_book": {
            b: dict(sorted(c.items())) for b, c in sorted(aligned_by_book.items())
        },
        "original_aligned_target_ids": len(aligned_target_ids),
        "original_unattested_target_ids": len(missing_aligned),
        "diagnostic_text_mismatch_coordinates": mismatching_verses,
        "automatic_missing_token_remaps": 0,
        "by_book": {b: dict(sorted(c.items())) for b, c in sorted(by_book.items())},
        "target_token_id_matches_certified": False,
    }


def compare_ot(osis_verses: dict[str, str], ot_candidate: dict):
    if ot_candidate.get("canon") != "ot" or ot_candidate.get("format") != "brsi-translation-alignment-candidate":
        raise ValueError("not the pinned OT candidate format")
    by_book: dict[str, Counter] = defaultdict(Counter)
    counts = Counter()
    for row in ot_candidate["records"]:
        target = row.get("target_lookup_ids")
        if not isinstance(target, list) or not target:
            raise ValueError("incomplete OT target selectors")
        present = all(isinstance(token, str) and TARGET_RE.fullmatch(token) and
                      token[:8] in osis_verses for token in target)
        status = "target_verse_present" if present else "target_verse_absent"
        counts[status] += 1
        for book in {x[:2] for x in target if isinstance(x, str)}:
            by_book[book][status] += 1
    if sum(counts.values()) != ot_candidate["coverage"]["records"]:
        raise ValueError("OT candidate total differs from reference census")
    return {
        "curated_ot_verses": sum(int(x[:2]) < 40 for x in osis_verses),
        "alignment_groups": len(ot_candidate["records"]),
        "target_reference_presence": dict(sorted(counts.items())),
        "target_reference_presence_by_book": {b: dict(sorted(c.items())) for b, c in sorted(by_book.items())},
        "target_word_inventory_present": False,
        "target_token_id_matches_certified": False,
        "automatic_cross_versification_fixes": 0,
    }


def build_report(alignment_manifest: dict, curated_lock: dict,
                 upstream_root: Path, curated_root: Path,
                 candidate_dir: Path) -> dict:
    if alignment_manifest.get("schema_version") != 1 or curated_lock.get("schema_version") != 1:
        raise ValueError("wrong manifest schema")
    if curated_lock.get("module_version") != "1.0.2" or curated_lock.get("sword_id") != "BRLSG1910":
        raise ValueError("wrong curated edition identity")
    meta_path = pinned_file(curated_root, curated_lock["osis_path"], curated_lock["osis_sha256"])
    metadata_path = curated_root / curated_lock["module_metadata_path"]
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (meta.get("version") != curated_lock["module_version"] or
        meta.get("sword_id") != curated_lock["sword_id"] or
        meta.get("versification") != curated_lock["versification"]):
        raise ValueError("curated module identity/versification mismatch")
    receipt = json.loads((candidate_dir / "receipt.json").read_text(encoding="utf-8"))
    if receipt["upstream_revision"] != alignment_manifest["revision"] or receipt["publication_approved"] is not False:
        raise ValueError("unaligned candidate source or publication boundary")
    pins = {p["key"]: p for p in alignment_manifest["inputs"]}
    groups = {p["canon"]: p for p in alignment_manifest["groups"]}
    nt_pin = pins[groups["nt"]["target"]]
    ot_pin = pins[groups["ot"]["target"]]
    nt_file = pinned_file(upstream_root, nt_pin["path"], nt_pin["sha256"])
    ot_file = pinned_file(upstream_root, ot_pin["path"], ot_pin["sha256"])
    target, target_census = read_target_tsv(nt_file)
    ot_targets, ot_census = read_target_tsv(ot_file)
    if ot_census["token_rows"] or ot_targets:
        raise ValueError("unexpected OT target inventory: new source audit required")
    for canon in ("nt", "ot"):
        path = candidate_dir / (canon + ".json")
        if sha256(path) != receipt["candidate_outputs"][canon]["sha256"]:
            raise ValueError("candidate differs from pinned receipt")
    nt_candidate = json.loads((candidate_dir / "nt.json").read_text(encoding="utf-8"))
    ot_candidate = json.loads((candidate_dir / "ot.json").read_text(encoding="utf-8"))
    if (nt_candidate["upstream_revision"] != alignment_manifest["revision"] or
            ot_candidate["upstream_revision"] != alignment_manifest["revision"]):
        raise ValueError("NT/OT candidate source differs from pinned revision")
    verses = read_osis(meta_path)
    nt = compare_nt(verses, target, target_census, nt_candidate)
    ot = compare_ot(verses, ot_candidate)
    return {
        "schema_version": 1,
        "kind": "curated-lsg-verse-surface-and-ot-reference-diagnostic",
        "clear_bible_revision": alignment_manifest["revision"],
        "curated_release": curated_lock["release_tag"],
        "curated_revision": curated_lock["revision"],
        "curated_osis_sha256": curated_lock["osis_sha256"],
        "curated_osis_verses": len(verses),
        "nt": nt,
        "ot": ot,
        "editions_proven_identical": False,
        "token_mapping_certified": False,
        "publication_approved": False,
        "unaligned_guesses_introduced": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-manifest", type=Path, required=True)
    parser.add_argument("--curated-lock", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--curated-root", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        json.loads(args.alignment_manifest.read_text(encoding="utf-8")),
        json.loads(args.curated_lock.read_text(encoding="utf-8")),
        args.upstream_root, args.curated_root, args.candidate_dir,
    )
    content = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    args.output.write_text(content, encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
