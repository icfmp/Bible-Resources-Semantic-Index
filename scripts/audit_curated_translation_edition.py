#!/usr/bin/env python3
"""Read-only edition comparison: pinned Clear.Bible LSG target TSV vs curated OSIS.

No source words, translation words, target remaps, public assets or publication.
An alphanumeric verse match is evidence about surface content only; it is NOT
tokenization/word-link certification or a license for guessed alignment IDs.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import gzip
import hashlib
import io
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


AUTHORIAL_WORD_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")


def word_stream(text: str) -> list[str]:
    """Diagnostic normalized word stream; never a Clear.Bible token-ID claim."""
    return [character_stream(m.group(0))
            for m in AUTHORIAL_WORD_RE.finditer(unicodedata.normalize("NFC", text))
            if character_stream(m.group(0))]


def build_authored_word_inventory(osis_verses: dict[str, str],
                                  curated_lock: dict) -> tuple[bytes, dict]:
    """Own edition-specific French word coordinates without inventing source IDs.

    A word coordinate identifies only a span of the *extracted authored verse
    body*, after Unicode NFC normalization and removal of OSIS notes/titles.
    It is never an OSIS byte offset or an upstream Clear.Bible target selector.
    Surfaces are excluded from the serialized inventory; strong exact-word and
    verse witnesses allow independent readback against the pinned OSIS file.
    """
    if not osis_verses or not curated_lock.get("osis_sha256"):
        raise ValueError("missing pinned curated OSIS or empty authored verses")
    canon_counts = defaultdict(Counter)
    by_verse = {}
    for bcv, raw_text in sorted(osis_verses.items()):
        if not BCV_RE.fullmatch(bcv) or not isinstance(raw_text, str):
            raise ValueError("invalid authored verse input")
        if not 1 <= int(bcv[:2]) <= 66:
            raise ValueError("unsupported authored book number")
        canon = "ot" if int(bcv[:2]) <= 39 else "nt"
        text = unicodedata.normalize("NFC", raw_text)
        words = []
        preceding_end = 0
        for match in AUTHORIAL_WORD_RE.finditer(text):
            word = match.group(0)
            if not any(char.isalnum() for char in word):
                raise ValueError("extracted non-word token")
            if match.start() < preceding_end:
                raise ValueError("overlapping authored word spans")
            preceding_end = match.end()
            words.append({
                "ordinal": len(words) + 1,
                "nfc_start_codepoint": match.start(),
                "nfc_end_codepoint": match.end(),
                "nfc_word_sha256": hashlib.sha256(word.encode("utf-8")).hexdigest(),
            })
        if character_stream(text) != "".join(
                character_stream(text[row["nfc_start_codepoint"]:
                                           row["nfc_end_codepoint"]])
                for row in words):
            raise ValueError("word inventory omitted alphanumeric verse characters")
        by_verse[bcv] = {
            "nfc_verse_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "nfc_codepoints": len(text),
            "words": words,
        }
        canon_counts[canon]["verses"] += 1
        canon_counts[canon]["words"] += len(words)
        if not words:
            canon_counts[canon]["zero_word_verses"] += 1
    coverage = {
        "ot": dict(sorted(canon_counts["ot"].items())),
        "nt": dict(sorted(canon_counts["nt"].items())),
        "verses": len(by_verse),
        "words": sum(len(row["words"]) for row in by_verse.values()),
    }
    payload = {
        "format": "brsi-curated-authorial-word-inventory",
        "schema_version": 1,
        "index_owner": "Bible Resources Semantic Index",
        "word_id_scheme": "curated_BCV_colon_one_based_word_ordinal",
        "tokenizer": "unicode_nfc_word_v1_apostrophes_and_hyphens_inside",
        "word_spans_relative_to": "extracted_NFC_OSIS_verse_body_not_XML_bytes",
        "source_text_embedded": False,
        "curated_release": curated_lock["release_tag"],
        "curated_osis_sha256": curated_lock["osis_sha256"],
        "status": "private_nonpublishing_unapproved",
        "coverage": coverage,
        "by_verse": by_verse,
    }
    return ((json.dumps(payload, sort_keys=True, ensure_ascii=False,
                        separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8"),
            coverage)


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


def _strip_external_nonletters(text: str) -> str:
    """Drop only material *outside* a token, never its apostrophes/hyphens."""
    start, end = 0, len(text)
    while start < end and not text[start].isalnum():
        start += 1
    while end > start and not text[end - 1].isalnum():
        end -= 1
    return text[start:end]


def classify_exact_word_surface(original_target: str, authored_word: str) -> str:
    """Require an attested full-word stream before classifying text evidence.

    The original Clear.Bible token and independently sourced LSG 1.0.2 word
    are not replaced or respelled. We record the strength of *observed*
    evidence, not a claim that a linguistic translation decision is right.
    """
    original = unicodedata.normalize("NFC", original_target)
    authored = unicodedata.normalize("NFC", authored_word)
    if not authored or not character_stream(authored):
        raise ValueError("cannot attest an empty French word")
    if character_stream(original) != character_stream(authored):
        raise ValueError("source token character stream differs from authored word")
    if original == authored:
        return "same_nfc_word_surface"
    if original.casefold() == authored.casefold():
        return "same_nfc_casefold_word_surface"
    if (_strip_external_nonletters(original).casefold() ==
            _strip_external_nonletters(authored).casefold()):
        return "same_word_with_external_punctuation_difference"
    return "only_alphanumeric_stream_matches"


def _nt_token_boundaries(source_text: str, targets: list[tuple[str, str]]):
    """Compare only surface character spans; do not create word/ID links."""
    original_text = unicodedata.normalize("NFC", source_text)
    word_matches = list(AUTHORIAL_WORD_RE.finditer(original_text))
    words = [character_stream(match.group()) for match in word_matches]
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
        attestation = None
        if status == "whole_one_word":
            ordinal = boundaries[offset] + 1
            match = word_matches[ordinal - 1]
            authored = match.group()
            evidence = classify_exact_word_surface(word, authored)
            attestation = {
                "word_ordinal": ordinal,
                "nfc_start_codepoint": match.start(),
                "nfc_end_codepoint": match.end(),
                "nfc_word_sha256": hashlib.sha256(authored.encode("utf-8")).hexdigest(),
                "original_target_nfc_sha256": hashlib.sha256(
                    unicodedata.normalize("NFC", word).encode("utf-8")).hexdigest(),
                "word_surface_evidence": evidence,
                "source_surface_compatible_with_authored_word": True,
            }
        result[identifier] = {
            "status": status,
            "word_ordinal": boundaries[offset] + 1 if status == "whole_one_word" else None,
            "attestation": attestation,
        }
        offset = end
    if offset != cumulative:
        raise ValueError("attempted span mapping across nonidentical character streams")
    return result


def contiguous_mismatch_runs(osis_verses: dict[str, str],
                             targets: dict[str, list[tuple[str, str]]],
                             mismatches: list[dict]) -> list[dict]:
    """Check whether adjacent differing verses have equal *combined* surfaces.

    This suggests segmentation/reference-boundary drift, but never reassigns a
    source or target verse, and never declares a legitimate versification.
    """
    ordered = [row["bcv"] for row in mismatches]
    runs = []
    current = []
    for key in ordered:
        if (current and (key[:5] != current[-1][:5]
                         or int(key[5:]) != int(current[-1][5:]) + 1)):
            if len(current) > 1:
                runs.append(current)
            current = []
        current.append(key)
    if len(current) > 1:
        runs.append(current)
    result = []
    for run in runs:
        source_chars = character_stream(" ".join(osis_verses[key] for key in run))
        target_chars = character_stream(" ".join(
            " ".join(surface for _, surface in targets[key]) for key in run
        ))
        result.append({
            "first_bcv": run[0],
            "last_bcv": run[-1],
            "verse_count": len(run),
            "combined_alphanumeric_stream_equal": source_chars == target_chars,
            "automatic_verse_reassignments": 0,
        })
    return result


def orthographic_character_stream(text: str) -> str:
    """Diagnostic French accent/ligature folding only, never text replacement."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = text.replace("œ", "oe").replace("æ", "ae")
    return "".join(char for char in text if char.isalnum() and
                   unicodedata.category(char) != "Mn")


def triage_verse_text_exceptions(osis_verses: dict[str, str],
                                 targets: dict[str, list[tuple[str, str]]],
                                 mismatches: list[dict],
                                 contiguous_runs: list[dict]) -> dict:
    """Classify evidence-backed edition differences, no hard-coded verse rules.

    A combined equal adjacent run is a potential boundary variant. Else the
    alphanumeric *opcode pattern* distinguishes missing curated characters
    in the original TSV from punctuation-insensitive orthographic variants.
    The output contains coordinates and counts, never biblical source text.
    """
    combined_equal = set()
    for run in contiguous_runs:
        if not run["combined_alphanumeric_stream_equal"]:
            continue
        if run["first_bcv"][:5] != run["last_bcv"][:5]:
            raise ValueError("cross-chapter mismatch run")
        lo, hi = int(run["first_bcv"][5:]), int(run["last_bcv"][5:])
        combined_equal.update(run["first_bcv"][:5] + f"{v:03d}"
                              for v in range(lo, hi + 1))
    counts = Counter()
    cases = []
    for item in mismatches:
        key = item["bcv"]
        if key not in osis_verses or key not in targets:
            raise ValueError("mismatch has no complete source/target verse witnesses")
        source = character_stream(osis_verses[key])
        target = character_stream(" ".join(text for _, text in targets[key]))
        if source == target:
            raise ValueError("reported mismatch is actually equal")
        if key in combined_equal:
            category = "adjacent_verse_boundary_partition"
        elif (orthographic_character_stream(osis_verses[key]) ==
              orthographic_character_stream(" ".join(text for _, text in targets[key]))):
            category = "orthographic_folding_only"
        else:
            operations = {tag for tag, _, _, _, _ in
                          difflib.SequenceMatcher(None, source, target,
                                                   autojunk=False).get_opcodes()
                          if tag != "equal"}
            if operations == {"delete"}:
                category = "original_target_tsv_omits_curated_characters"
            elif operations == {"insert"}:
                category = "original_target_tsv_adds_characters"
            else:
                category = "other_unresolved_text_difference"
        counts[category] += 1
        cases.append({"bcv": key, "category": category,
                      "original_alignment_changed": False,
                      "curated_scripture_changed": False,
                      "automatic_verse_reassignment": False})
    if sum(counts.values()) != len(mismatches):
        raise ValueError("exception triage did not classify the full original census")
    return {"categories": dict(sorted(counts.items())),
            "cases": sorted(cases, key=lambda row: row["bcv"]),
            "automated_alignment_corrections": 0,
            "orthographic_equivalence_not_word_link_proof": True}


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
                for identifier, projection in classified.items():
                    category = projection["status"]
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
    adjacent = contiguous_mismatch_runs(source, targets, mismatching_verses)
    exception_triage = triage_verse_text_exceptions(source, targets,
                                                    mismatching_verses, adjacent)
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
        "text_exception_triage": exception_triage,
        "adjacent_text_mismatch_runs": adjacent,
        "adjacent_mismatch_verses_with_identical_combined_stream": sum(
            item["verse_count"] for item in adjacent if item["combined_alphanumeric_stream_equal"]
        ),
        "automatic_missing_token_remaps": 0,
        "by_book": {b: dict(sorted(c.items())) for b, c in sorted(by_book.items())},
        "target_token_id_matches_certified": False,
    }


def build_private_nt_word_index(osis_verses: dict[str, str],
                                 targets: dict[str, list[tuple[str, str]]],
                                 nt_candidate: dict,
                                 curated_lock: dict,
                                 alignment_revision: str) -> tuple[bytes, dict]:
    """Stage original-MACULA-to-curated-word-position CANDIDATES (never approve).

    A candidate requires an original attested 1:1 source/target selector,
    an identical verse alphanumeric stream and an exact one-curated-word
    boundary. No guess can create a missing target token or change a verse.
    """
    target_positions = {}
    for bcv, rows in targets.items():
        text = osis_verses.get(bcv)
        aligned = text is not None and character_stream(text) == character_stream(
            " ".join(surface for _, surface in rows))
        if aligned:
            target_positions.update(_nt_token_boundaries(text, rows))
        else:
            for token_id, _ in rows:
                target_positions[token_id] = {"status": "verse_text_mismatch",
                                               "word_ordinal": None}

    rows = []
    census = Counter()
    for record in nt_candidate["records"]:
        sources = record["source_lookup_ids"]
        targets_original = record["target_lookup_ids"]
        if not isinstance(sources, list) or not isinstance(targets_original, list):
            raise ValueError("invalid original source/target selectors in candidate")
        reason = None
        curated_bcv = None
        ordinal = None
        if len(sources) != 1 or len(targets_original) != 1:
            reason = "non_one_to_one_selector"
        elif not isinstance(sources[0], str) or not isinstance(targets_original[0], str):
            reason = "invalid_original_selector"
        else:
            target_id = targets_original[0]
            projection = target_positions.get(target_id)
            if projection is None:
                reason = "unattested_target_selector"
            elif projection["status"] != "whole_one_word":
                reason = projection["status"]
            else:
                source_bcv = sources[0][1:9]
                curated_bcv = target_id[:8]
                if source_bcv != curated_bcv:
                    # Do not silently merge dissimilar versification coordinates.
                    reason = "cross_verse_selector"
                    curated_bcv = None
                else:
                    ordinal = projection["word_ordinal"]
        status = "surface_word_position_candidate" if reason is None else "unresolved"
        attestation = projection["attestation"] if reason is None else None
        if attestation is not None:
            census["word_surface_evidence_" + attestation["word_surface_evidence"]] += 1
            if attestation["word_ordinal"] != ordinal:
                raise ValueError("exact authored word witness differs from candidate position")
        census[status] += 1
        if reason:
            census["reason_" + reason] += 1
        rows.append({
            "original_ordinal": record["ordinal"],
            "original_macula_ids": sources,
            "original_target_ids": targets_original,
            "curated_bcv": curated_bcv,
            "curated_diagnostic_word_ordinal": ordinal,
            "status": status,
            "reason": reason,
            "authored_word_surface_attestation": attestation,
            "editorially_approved": False,
        })
    if len(rows) != nt_candidate["coverage"]["records"]:
        raise ValueError("generated index count differs from original source")
    if census["surface_word_position_candidate"] + census["unresolved"] != len(rows):
        raise ValueError("generated index statuses do not partition original source")
    if sum(count for category, count in census.items()
           if category.startswith("word_surface_evidence_")) != census["surface_word_position_candidate"]:
        raise ValueError("attested word surface evidence does not partition candidate links")
    # The maintained BRSI output is a real bidirectional index, not a
    # runtime adapter applied to the original Clear.Bible lookup. Preserve
    # unresolved rows and source IDs for later evidence-based corrections.
    by_original_macula_id = defaultdict(list)
    by_curated_word = defaultdict(list)
    for row in rows:
        ordinal = row["original_ordinal"]
        for original_id in row["original_macula_ids"]:
            if not isinstance(original_id, str) or not original_id:
                raise ValueError("invalid original MACULA source ID")
            by_original_macula_id[original_id].append(ordinal)
        if row["status"] == "surface_word_position_candidate":
            key = (row["curated_bcv"] + ":" +
                   str(row["curated_diagnostic_word_ordinal"]))
            by_curated_word[key].append(ordinal)
    if sum(map(len, by_curated_word.values())) != census["surface_word_position_candidate"]:
        raise ValueError("curated-word inverse index is incomplete")
    payload = {
        "format": "brsi-curated-translation-word-index-candidate",
        "index_owner": "Bible Resources Semantic Index",
        "provenance": "original_clear_bible_plus_reviewed_brsi_decisions",
        "schema_version": 1,
        "source_alignment_revision": alignment_revision,
        "curated_release": curated_lock["release_tag"],
        "curated_osis_sha256": curated_lock["osis_sha256"],
        "status": "private_nonpublishing_unapproved",
        "original_alignment_records": len(rows),
        "coverage": dict(sorted(census.items())),
        "by_original_macula_id": dict(sorted(by_original_macula_id.items())),
        "by_curated_word": dict(sorted(by_curated_word.items())),
        "rows": rows,
    }
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    return raw, dict(sorted(census.items()))


def build_private_ot_verse_index(osis_verses: dict[str, str],
                                 ot_candidate: dict,
                                 curated_lock: dict,
                                 alignment_revision: str) -> tuple[bytes, dict]:
    """Own the OT index without fabricating French word identities.

    Every original Hebrew→French selector survives, including genuine source
    versus target verse-coordinate differences. Only independently attested
    *target verse presence* is indexed until an original target-word corpus
    allows a word-level validation. Original target ordinals are evidence,
    never silently reinterpreted as positions in curated LSG.
    """
    if (ot_candidate.get("canon") != "ot" or
            ot_candidate.get("format") != "brsi-translation-alignment-candidate"):
        raise ValueError("not the original OT candidate format")
    original_rows = ot_candidate.get("records")
    if not isinstance(original_rows, list) or len(original_rows) != ot_candidate.get("coverage", {}).get("records"):
        raise ValueError("OT source record census differs from original receipt")
    row_index = []
    by_original_macula_id: dict[str, list[int]] = defaultdict(list)
    by_curated_verse: dict[str, list[int]] = defaultdict(list)
    census = Counter()
    for ordinal, record in enumerate(original_rows):
        if not isinstance(record, dict) or record.get("ordinal") != ordinal:
            raise ValueError("OT original record ordinal altered")
        source = record.get("source_lookup_ids")
        target = record.get("target_lookup_ids")
        if not isinstance(source, list) or not isinstance(target, list):
            raise ValueError("invalid original OT source or target selector array")
        for identifier in source:
            if not isinstance(identifier, str) or not re.fullmatch(r"o[0-9]{11,12}", identifier):
                raise ValueError("invalid OT MACULA original selector")
            by_original_macula_id[identifier].append(ordinal)
        targets = []
        for identifier in target:
            if not isinstance(identifier, str) or not TARGET_RE.fullmatch(identifier):
                raise ValueError("invalid OT French original selector")
            targets.append(identifier[:8])
        source_verses = sorted({identifier[1:9] for identifier in source})
        target_verses = sorted(set(targets))
        target_verse_present = bool(target_verses) and all(
            verse in osis_verses and int(verse[:2]) < 40 for verse in target_verses
        )
        differing = bool(source_verses and target_verses and
                         set(source_verses) != set(target_verses))
        if not source:
            status = "unresolved_no_original_macula_word"
        elif not target_verse_present:
            status = "unresolved_target_verse_not_attested"
        else:
            status = "verse_reference_present_word_unverified"
            for verse in target_verses:
                by_curated_verse[verse].append(ordinal)
        census[status] += 1
        if differing:
            census["different_original_source_target_verse_coordinates"] += 1
        row_index.append({
            "original_ordinal": ordinal,
            "original_macula_ids": source,
            "original_target_ids": target,
            "original_source_verses": source_verses,
            "curated_target_verses": target_verses,
            "original_source_target_verse_differ": differing,
            "status": status,
            "curated_word_position": None,
            "target_word_inventory_verified": False,
            "editorially_approved": False,
        })
    if sum(census.get(key, 0) for key in (
        "unresolved_no_original_macula_word",
        "unresolved_target_verse_not_attested",
        "verse_reference_present_word_unverified"
    )) != len(original_rows):
        raise ValueError("OT candidates lost source records")
    if sum(map(len, by_curated_verse.values())) < census["verse_reference_present_word_unverified"]:
        raise ValueError("OT target verse index missing records")
    payload = {
        "format": "brsi-curated-translation-verse-index-candidate",
        "schema_version": 1,
        "canon": "ot",
        "index_owner": "Bible Resources Semantic Index",
        "provenance": "original_clear_bible_plus_reviewed_brsi_decisions",
        "source_alignment_revision": alignment_revision,
        "curated_release": curated_lock["release_tag"],
        "curated_osis_sha256": curated_lock["osis_sha256"],
        "status": "private_nonpublishing_unapproved",
        "word_positions_available": False,
        "original_alignment_records": len(row_index),
        "coverage": dict(sorted(census.items())),
        "by_original_macula_id": dict(sorted(by_original_macula_id.items())),
        "by_curated_verse": dict(sorted(by_curated_verse.items())),
        "rows": row_index,
    }
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    return raw, dict(sorted(census.items()))


def write_private_index(raw: bytes, output: Path, coverage: dict) -> dict:
    """Runner-local deterministic index and receipt, never inside Git."""
    if output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("private alignment candidate must not be written in checkout")
    with io.BytesIO() as buffer:
        with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0,
                           compresslevel=9) as archive:
            archive.write(raw)
        compressed = buffer.getvalue()
    output.write_bytes(compressed)
    return {
        "gzip_sha256": hashlib.sha256(compressed).hexdigest(),
        "gzip_bytes": len(compressed),
        "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
        "uncompressed_bytes": len(raw),
        "coverage": coverage,
        "editorially_approved": False,
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
                 candidate_dir: Path, index_output: Path | None = None,
                 ot_index_output: Path | None = None,
                 word_inventory_output: Path | None = None) -> dict:
    if alignment_manifest.get("schema_version") != 1 or curated_lock.get("schema_version") != 1:
        raise ValueError("wrong manifest schema")
    if not all(isinstance(curated_lock.get(key), str) and curated_lock[key].strip()
               for key in ("module_version", "sword_id", "versification", "release_tag", "revision")):
        raise ValueError("missing exact curated edition identity")
    meta_path = pinned_file(curated_root, curated_lock["osis_path"], curated_lock["osis_sha256"])
    metadata_relative = Path(curated_lock["module_metadata_path"])
    if metadata_relative.is_absolute() or ".." in metadata_relative.parts:
        raise ValueError("unsafe curated module metadata path")
    metadata_path = curated_root / metadata_relative
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
    word_inventory_receipt = None
    if word_inventory_output is not None:
        raw, coverage = build_authored_word_inventory(verses, curated_lock)
        word_inventory_receipt = write_private_index(
            raw, word_inventory_output, coverage)
    index_receipt = None
    if index_output is not None:
        raw, coverage = build_private_nt_word_index(
            verses, target, nt_candidate, curated_lock, alignment_manifest["revision"]
        )
        index_receipt = write_private_index(raw, index_output, coverage)
    ot_index_receipt = None
    if ot_index_output is not None:
        raw, coverage = build_private_ot_verse_index(
            verses, ot_candidate, curated_lock, alignment_manifest["revision"]
        )
        ot_index_receipt = write_private_index(raw, ot_index_output, coverage)
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
        "private_nt_word_index": index_receipt,
        "private_ot_verse_index": ot_index_receipt,
        "private_authorial_word_inventory": word_inventory_receipt,
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
    parser.add_argument("--index-output", type=Path)
    parser.add_argument("--ot-index-output", type=Path)
    parser.add_argument("--word-inventory-output", type=Path)
    args = parser.parse_args()
    report = build_report(
        json.loads(args.alignment_manifest.read_text(encoding="utf-8")),
        json.loads(args.curated_lock.read_text(encoding="utf-8")),
        args.upstream_root, args.curated_root, args.candidate_dir,
        args.index_output, args.ot_index_output, args.word_inventory_output,
    )
    content = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    args.output.write_text(content, encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
