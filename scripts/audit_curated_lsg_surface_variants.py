#!/usr/bin/env python3
"""Audit safely distinguishable French word surfaces in the locked MACULA index.

Read-only, exact-source analysis of *unlinked* MACULA source words whose
Aquifer French target word is not NFC-identical to any word in the authored
Bible Resources LSG 1.0.2 target verse. No alignment IDs or Scripture are
changed, and this script does not add a link to the BRSI index.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts" / "build_curated_lsg_word_correspondence.py"
spec = importlib.util.spec_from_file_location("brsi_locked_word_bridge", BRIDGE)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

# For diagnosis only. Substitution is never applied to the source or OSIS.
LIGATURES = str.maketrans({"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE"})


def no_ligatures(surface: str) -> str:
    return surface.translate(LIGATURES)


def no_accents(surface: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", surface)
        if unicodedata.category(c) != "Mn"
    )


def key_word(surface: str, method: str) -> str:
    surface = unicodedata.normalize("NFC", surface)
    if method == "case_only":
        return surface.casefold()
    if method == "ligature_only":
        return no_ligatures(surface)
    if method == "case_and_ligature":
        return no_ligatures(surface).casefold()
    if method == "accent_only":
        return no_accents(surface)
    if method == "apostrophe_only":
        return surface.replace("’", "'")
    raise ValueError("unsupported diagnostic comparison")


METHODS = ("case_only", "ligature_only", "case_and_ligature",
           "accent_only", "apostrophe_only")


def classify_absent_french_target(
        source_word: str,
        original_verse_words: list[str],
        authored_verse_words: list[str],
) -> tuple[str, str | None]:
    """Classify *word location hypotheses*, never translation equivalence.

    A positive unique class requires one original occurrence and one authored
    occurrence of the same strictly described normalized full-word surface.
    Repeats, even when numerically close to a target selector, abstain.
    """
    source_word = unicodedata.normalize("NFC", source_word)
    if source_word in authored_verse_words:
        return "same_surface_not_located_or_repeated", None
    possibilities = []
    for method in METHODS:
        target_key = key_word(source_word, method)
        original_keys = [key_word(w, method) for w in original_verse_words]
        authored_keys = [key_word(w, method) for w in authored_verse_words]
        if target_key not in authored_keys:
            continue
        # A strict key must actually differ from the original French word,
        # rather than becoming an accidental match because of arbitrary case.
        if (original_keys.count(target_key) == 1 and
                authored_keys.count(target_key) == 1):
            matched = authored_verse_words[authored_keys.index(target_key)]
            if matched != source_word:
                possibilities.append((method, matched))
        else:
            possibilities.append((method + "_ambiguous", None))
    unambiguous = [(method, matched) for method, matched in possibilities
                   if not method.endswith("_ambiguous")]
    if not unambiguous:
        return ("normalized_candidate_ambiguous", None) if possibilities else (
            "no_strict_orthographic_candidate", None)
    # Multiple normalization methods may identify the same authored word.
    # Select the narrowest diagnostic, not any guessed target ordinal.
    methods = {matched for _, matched in unambiguous}
    if len(methods) != 1:
        return "conflicting_normalized_candidates", None
    return unambiguous[0]


def audit_target_surfaces(aquifer_root: Path, authored: dict[str, str],
                          original_unlocated: dict[str, str],
                          *, min_chapters: int = 1) -> dict:
    """Classify every source ID in the previously pinned exact-absence queue."""
    missing_sources = {
        source_id for source_id, reason in original_unlocated.items()
        if reason == "exact_french_word_absent_from_curated_verse"
    }
    files = sorted((aquifer_root / "fra" / "alignments" / "json").glob(
        "*.alignment.json"))
    if len(files) < min_chapters:
        raise ValueError("Aquifer pinned chapter set incomplete")

    original_words_by_verse: dict[str, dict[str, str]] = defaultdict(dict)
    targets_by_source: dict[str, set[str]] = defaultdict(set)
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("format") != "alignment":
            raise ValueError("unrecognized Aquifer alignment chapter")
        for group in doc.get("groups", []):
            if group.get("type") != "translation":
                continue
            # Preserve the entire original target verse inventory, including
            # original target words explicitly declared unaligned to source.
            for record in group.get("records", []):
                parsed_targets = [bridge.split_selector(value)
                                  for value in record.get("target", [])]
                parsed_targets = [entry for entry in parsed_targets
                                  if entry is not None]
                for target_id, surface in parsed_targets:
                    old = original_words_by_verse[target_id[:8]].setdefault(
                        target_id, surface)
                    if old != surface:
                        raise ValueError("conflicting original Aquifer French word")
                for src in record.get("source", []):
                    original_source = bridge.split_selector(src)
                    if original_source is None:
                        continue
                    source_id = original_source[0]
                    source_id = ("o" if int(source_id[:2]) < 40 else "n") + source_id
                    if source_id in missing_sources:
                        targets_by_source[source_id].update(
                            target_id for target_id, _ in parsed_targets)
            for original in group.get("meta", {}).get(
                    "nonEquivalent", {}).get("target", []):
                parsed = bridge.split_selector(original)
                if parsed is None:
                    continue
                target_id, surface = parsed
                old = original_words_by_verse[target_id[:8]].setdefault(
                    target_id, surface)
                if old != surface:
                    raise ValueError("conflicting original unaligned French word")
    if set(targets_by_source) != missing_sources:
        missing = sorted(missing_sources - set(targets_by_source))
        raise ValueError(
            f"original source target-absence audit incomplete: {len(missing)} missing")

    word_cache: dict[str, list[str]] = {}
    original_cache: dict[str, list[str]] = {}
    status_by_source = {}
    counters = defaultdict(Counter)
    examples = defaultdict(list)
    for source_id in sorted(missing_sources):
        results = set()
        for target_id in sorted(targets_by_source[source_id]):
            verse = target_id[:8]
            if verse not in authored:
                results.add(("authored_verse_absent", None))
                continue
            if verse not in word_cache:
                word_cache[verse] = [
                    word for word, _, _ in bridge.word_tokens(authored[verse])]
            if verse not in original_cache:
                originals = original_words_by_verse[verse]
                original_cache[verse] = [
                    surface for _, surface in sorted(
                        originals.items(), key=lambda kv: (
                            int(kv[0][8:11]), int(kv[0][11:] or "0")))]
            surface = original_words_by_verse[verse].get(target_id)
            if surface is None:
                results.add(("original_target_surface_missing", None))
                continue
            result = classify_absent_french_target(
                surface, original_cache[verse], word_cache[verse])
            results.add(result)
            if result[1] is not None and len(examples[result[0]]) < 5:
                examples[result[0]].append({
                    "original_macula_id": source_id,
                    "original_target_id": target_id,
                    "curated_verse": verse,
                    "original_surface_sha256": hashlib.sha256(
                        surface.encode("utf-8")).hexdigest(),
                    "matched_curated_word_sha256": hashlib.sha256(
                        result[1].encode("utf-8")).hexdigest(),
                })
        if len(results) == 1:
            status = next(iter(results))[0]
        else:
            status = "multiple_target_diagnostics"
        status_by_source[source_id] = status
        canon = "ot" if source_id.startswith("o") else "nt"
        counters[canon][status] += 1

    baseline = {
        canon: sum(1 for source in missing_sources
                   if source.startswith("o" if canon == "ot" else "n"))
        for canon in ("nt", "ot")
    }
    for canon in ("nt", "ot"):
        if sum(counters[canon].values()) != baseline[canon]:
            raise ValueError("incomplete French orthography diagnostic census")

    return {
        "format": "brsi-french-surface-difference-readonly-audit",
        "schema_version": 1,
        "purpose": "classify_only_no_automatic_translation_link",
        "original_unlinked_exact_word_absence": baseline,
        "original_unlinked_exact_word_absence_total": len(missing_sources),
        "by_canon": {canon: dict(sorted(counters[canon].items()))
                     for canon in ("nt", "ot")},
        "source_ids_by_diagnostic": status_by_source,
        "sample_source_word_hashes_only": dict(sorted(examples.items())),
        "source_french_text_modified": False,
        "original_source_ids_modified": False,
        "linguistic_links_automatically_approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aquifer-root", required=True, type=Path)
    parser.add_argument("--curated-root", required=True, type=Path)
    parser.add_argument("--curated-lock", required=True, type=Path)
    parser.add_argument("--original-index", required=True, type=Path)
    parser.add_argument("--correspondence-lock", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--min-chapters", type=int, default=1188)
    args = parser.parse_args()
    if args.report.resolve().is_relative_to(ROOT):
        raise ValueError("private source corpus audit output must not be in repository")
    curated = json.loads(args.curated_lock.read_text(encoding="utf-8"))
    baseline = json.loads(args.correspondence_lock.read_text(encoding="utf-8"))
    if bridge.ed.sha256(args.original_index) != baseline["gzip_sha256"]:
        raise ValueError("MACULA index does not match pinned complete original receipt")
    index = json.loads(gzip.decompress(args.original_index.read_bytes()))
    if (index["source_aquifer_revision"] != baseline["source_aquifer_revision"] or
        index["source_clear_bible_revision"] != baseline["source_clear_bible_revision"] or
        index["curated_osis_sha256"] != baseline["curated_osis_sha256"] or
        index["curated_osis_sha256"] != curated["osis_sha256"]):
        raise ValueError("French source edition or alignment witness mismatch")
    osis = bridge.ed.pinned_file(args.curated_root, curated["osis_path"],
                                curated["osis_sha256"])
    report = audit_target_surfaces(
        args.aquifer_root,
        bridge.ed.read_osis(osis),
        index["unlocated_french_target_cause_by_original_macula_id"],
        min_chapters=args.min_chapters)
    expected = baseline["unlocated_french_target_cause_counts"]
    if (report["original_unlinked_exact_word_absence"]["nt"] !=
        expected["nt"]["exact_french_word_absent_from_curated_verse"] or
        report["original_unlinked_exact_word_absence"]["ot"] !=
        expected["ot"]["exact_french_word_absent_from_curated_verse"]):
        raise ValueError("full-source exact-word absence audit baseline changed")
    report["curated_osis_sha256"] = curated["osis_sha256"]
    report["clear_bible_revision"] = index["source_clear_bible_revision"]
    report["aquifer_revision"] = index["source_aquifer_revision"]
    report["correspondence_index_sha256"] = baseline["gzip_sha256"]
    # The detailed per-source report remains private. CI pins a compact,
    # entirely text-free receipt while permitting targeted editorial review.
    counts = {k: report[k] for k in (
        "format", "schema_version", "purpose",
        "original_unlinked_exact_word_absence",
        "original_unlinked_exact_word_absence_total",
        "by_canon", "source_french_text_modified",
        "original_source_ids_modified", "linguistic_links_automatically_approved",
        "curated_osis_sha256", "clear_bible_revision", "aquifer_revision",
        "correspondence_index_sha256")}
    counts["full_diagnostic_sha256"] = hashlib.sha256(
        (json.dumps(report, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False) + "\n").encode("utf-8")).hexdigest()
    args.report.write_text(json.dumps(counts, ensure_ascii=False,
                                       sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, sort_keys=True, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
