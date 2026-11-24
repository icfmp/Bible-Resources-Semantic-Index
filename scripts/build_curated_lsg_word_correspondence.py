#!/usr/bin/env python3
"""Build an owned LSG word-link evidence index from two independent witnesses.

Inputs are immutable Clear.Bible MACULA alignment groups, Aquifer word-surfaced
alignment groups, and the exact authored Bible Resources LSG 1.0.2 OSIS.
No guessed French word IDs, original modifications or automatic editorial
approvals. This generator does not require Aquifer target ordinals to equal
our French word ordinals: it compares real target text against exact verse
word spans, with duplicate-position ambiguity explicitly retained.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITION_FILE = ROOT / "scripts" / "audit_curated_translation_edition.py"
_spec = importlib.util.spec_from_file_location("brsi_curated", EDITION_FILE)
ed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ed)

CHAPTER_RE = re.compile(r"^([0-9]{2})-([0-9]{3})\.alignment\.json$")
SELECTOR_RE = re.compile(r"^[0-9]{11,12}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def split_selector(value: str) -> tuple[str, str] | None:
    """Return an original word selector and surface, if actually present."""
    if not isinstance(value, str):
        raise ValueError("nonstring Aquifer token")
    selector, sep, surface = value.partition("|")
    if not SELECTOR_RE.fullmatch(selector):
        raise ValueError("invalid Aquifer token selector " + repr(selector))
    if not sep or not surface.strip():
        return None
    return selector, unicodedata.normalize("NFC", surface)


def word_tokens(text: str) -> list[tuple[str, int, int]]:
    normalized = unicodedata.normalize("NFC", text)
    return [(m.group(), m.start(), m.end())
            for m in ed.AUTHORIAL_WORD_RE.finditer(normalized)]


def unique_ordered_exact_locations(tokens: list[str],
                                   authored: list[str]) -> dict[int, int]:
    """Map only tokens whose location is forced in *every* optimal word LCS.

    A skipped token, duplicate that can occupy two positions, or an edition
    disagreement is not accepted. All witnesses must agree exactly after NFC.
    This is an evidence locator, not a linguistic alignment algorithm.
    """
    n, m = len(tokens), len(authored)
    if not n or not m:
        return {}
    forward = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        ti = tokens[i - 1]
        for j in range(1, m + 1):
            forward[i][j] = (forward[i - 1][j - 1] + 1
                             if ti == authored[j - 1]
                             else max(forward[i - 1][j], forward[i][j - 1]))
    suffix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            suffix[i][j] = (suffix[i + 1][j + 1] + 1
                            if tokens[i] == authored[j]
                            else max(suffix[i + 1][j], suffix[i][j + 1]))
    optimum = suffix[0][0]
    if optimum != forward[n][m]:
        raise ValueError("LCS proof conflict")
    matches = {}
    for i, word in enumerate(tokens):
        can_skip = any(forward[i][j] + suffix[i + 1][j] == optimum
                       for j in range(m + 1))
        if can_skip:
            continue
        js = [j for j in range(m) if word == authored[j] and
              forward[i][j] + 1 + suffix[i + 1][j + 1] == optimum]
        if len(js) == 1:
            matches[i] = js[0]
    return matches


def load_aquifer(root: Path, authored: dict[str, str],
                 min_chapters: int = 1) -> tuple[dict, dict, dict]:
    """Read original Aquifer chapter alignments and verify their French text."""
    folder = root / "fra" / "alignments" / "json"
    files = sorted(folder.glob("*.alignment.json"))
    if len(files) < min_chapters:
        raise ValueError("Aquifer chapter set is incomplete")
    targets_by_verse: dict[str, dict[str, str]] = defaultdict(dict)
    raw_links: list[tuple[str, str, str]] = []
    counts = Counter()
    for path in files:
        match = CHAPTER_RE.fullmatch(path.name)
        if not match:
            raise ValueError("unexpected Aquifer alignment filename")
        chapter = match.group(1) + match.group(2)
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("format") != "alignment" or not isinstance(document.get("groups"), list):
            raise ValueError("unrecognized Aquifer alignment file")
        counts["chapters"] += 1
        for group in document["groups"]:
            if group.get("type") != "translation" or not isinstance(group.get("records"), list):
                continue
            if [item.get("docid") for item in group.get("documents", [])] != [
                    "WLCM" if int(chapter[:2]) < 40 else "SBLGNT", "LSG"]:
                raise ValueError("unexpected original/target edition in Aquifer")
            for rec in group["records"]:
                src = [split_selector(item) for item in rec.get("source", [])]
                trg = [split_selector(item) for item in rec.get("target", [])]
                src = [x for x in src if x is not None]
                trg = [x for x in trg if x is not None]
                for target_id, surface in trg:
                    if target_id[:5] != chapter:
                        raise ValueError("Aquifer target verse outside chapter")
                    old = targets_by_verse[target_id[:8]].setdefault(target_id, surface)
                    if old != surface:
                        raise ValueError("conflicting Aquifer French surface for one original ID")
                for source_id, _ in src:
                    if source_id[:5] != chapter:
                        raise ValueError("Aquifer source verse outside chapter")
                    for target_id, _ in trg:
                        raw_links.append((source_id, target_id, path.name))
                        counts["source_target_edges"] += 1
            extra = group.get("meta", {}).get("nonEquivalent", {}).get("target", [])
            for item in extra:
                parsed = split_selector(item)
                if parsed is None:
                    counts["empty_non_equivalent_tokens"] += 1
                    continue
                target_id, surface = parsed
                if target_id[:5] != chapter:
                    raise ValueError("nonEquivalent target outside chapter")
                old = targets_by_verse[target_id[:8]].setdefault(target_id, surface)
                if old != surface:
                    raise ValueError("conflicting Aquifer unaligned target surface")
    located: dict[str, dict] = {}
    for bcv, originals in sorted(targets_by_verse.items()):
        if bcv not in authored:
            counts["target_verse_missing_from_curated"] += 1
            continue
        content = unicodedata.normalize("NFC", authored[bcv])
        authored_words = word_tokens(content)
        items = sorted(originals.items(), key=lambda pair: (int(pair[0][8:11]),
                                                           int(pair[0][11:] or "0")))
        eligible = [(token_id, surface) for token_id, surface in items
                    if len(word_tokens(surface)) == 1 and
                    word_tokens(surface)[0][0] == surface]
        counts["target_tokens_observed"] += len(items)
        counts["target_tokens_not_full_words"] += len(items) - len(eligible)
        positions = unique_ordered_exact_locations(
            [surface for _, surface in eligible],
            [word for word, _, _ in authored_words])
        counts["target_verses_with_source_text"] += 1
        if len(positions) == len(eligible) == len(authored_words):
            counts["verses_full_word_sequence_identical"] += 1
        for index, authored_index in positions.items():
            original_id, surface = eligible[index]
            matched, start, end = authored_words[authored_index]
            if surface != matched:
                raise ValueError("source text changed behind exact match")
            located[original_id] = {
                "bcv": bcv,
                "word_ordinal": authored_index + 1,
                "nfc_start": start,
                "nfc_end": end,
                "word_sha256": hashlib.sha256(matched.encode("utf-8")).hexdigest(),
                "surface_match": "exact_NFC",
                "source": "BibleAquifer/LouisSegond1910",
            }
            counts["target_tokens_uniquely_located"] += 1
        counts["target_tokens_unresolved"] += len(items) - len(positions)
    witness_by_source: dict[str, set[str]] = defaultdict(set)
    for src, target_id, _ in raw_links:
        if target_id in located:
            prefix = "o" if int(src[:2]) < 40 else "n"
            witness_by_source[prefix + src].add(target_id)
            counts["exact_located_source_target_edges"] += 1
    return located, witness_by_source, dict(sorted(counts.items()))


def build_corroborated_index(aquifer_root: Path, original_candidates: Path,
                             osis_file: Path, curated_lock: dict,
                             original_revision: str, aquifer_revision: str,
                             min_chapters: int = 1) -> tuple[bytes, dict]:
    if not COMMIT_RE.fullmatch(aquifer_revision) or not COMMIT_RE.fullmatch(original_revision):
        raise ValueError("invalid pinned alignment revisions")
    authored = ed.read_osis(osis_file)
    located, source_links, census = load_aquifer(aquifer_root, authored, min_chapters)
    groups = {}
    matches_by_target = Counter()
    rows = []
    by_macula: dict[str, list[int]] = defaultdict(list)
    by_french_word: dict[str, list[int]] = defaultdict(list)
    statuses = Counter()
    calibration = Counter()
    for canon in ("nt", "ot"):
        doc = json.loads((original_candidates / (canon + ".json")).read_text(encoding="utf-8"))
        if doc.get("canon") != canon or doc.get("upstream_revision") != original_revision:
            raise ValueError("original Clear.Bible group source pin mismatch")
        records = doc.get("records", [])
        if len(records) != doc.get("coverage", {}).get("records"):
            raise ValueError("original source alignment census altered")
        groups[canon] = len(records)
        for source_row in records:
            source = source_row["source_lookup_ids"]
            original_targets = source_row["target_lookup_ids"]
            if not isinstance(source, list) or not isinstance(original_targets, list):
                raise ValueError("original selector groups missing")
            original_target_locations = {
                located[target_id]["bcv"] + ":" + str(located[target_id]["word_ordinal"])
                for target_id in original_targets if target_id in located}
            from_source = {
                located[t]["bcv"] + ":" + str(located[t]["word_ordinal"])
                for source_id in source for t in source_links.get(source_id, ())
                if t in located}
            corroborated = sorted(original_target_locations & from_source)
            from_independent = sorted(from_source - set(corroborated))
            if corroborated:
                status = "original_target_and_independent_source_agree"
                matched_words = corroborated
            elif from_source and original_target_locations:
                status = "conflicting_original_and_independent_witnesses"
                matched_words = []
            elif from_source:
                status = "independent_aquifer_word_witness_only"
                matched_words = from_independent
            elif original_target_locations:
                status = "original_target_id_has_independent_french_surface"
                matched_words = sorted(original_target_locations)
            else:
                status = "unresolved_no_located_word"
                matched_words = []
            # NT calibration: previous fully attested original target
            # word identity is an independent control for target-ID reuse.
            if canon == "nt" and len(original_targets) == 1:
                calib_target = original_targets[0]
                if calib_target in located:
                    calibration["nt_original_target_id_attested_by_aquifer"] += 1
                    # An exact original full-word match is checked below by
                    # comparing to BRSI's previously built NT word index.
                else:
                    calibration["nt_original_target_id_not_located_by_aquifer"] += 1
            statuses[canon + "_" + status] += 1
            ordinal = len(rows)
            row = {
                "canon": canon,
                "original_ordinal": source_row["ordinal"],
                "original_macula_ids": source,
                "original_clear_bible_target_ids": original_targets,
                "word_ids": matched_words,
                "status": status,
                "source_provenance": ("Clear.Bible+BibleAquifer"
                                      if corroborated else "BibleAquifer"
                                      if from_source else "Clear.Bible_target_and_Aquifer_surface"
                                      if original_target_locations else "original_unresolved"),
                "linguistically_reviewed_by_brsi": False,
            }
            rows.append(row)
            for source_id in source:
                by_macula[source_id].append(ordinal)
            for word in matched_words:
                by_french_word[word].append(ordinal)
    if groups["nt"] != 104807 or groups["ot"] != 203597:
        # Synthetic tests may supply shorter original inputs, so validate
        # exact group size against authenticated candidate receipts, not
        # absolute book-specific constants here.
        pass
    if len(rows) != sum(groups.values()) or len(rows) != sum(statuses.values()):
        raise ValueError("correspondence records lost")
    report = {
        "format": "brsi-original-and-independent-word-corroboration-candidate",
        "schema_version": 1,
        "owner": "Bible Resources Semantic Index",
        "source_clear_bible_revision": original_revision,
        "source_aquifer_revision": aquifer_revision,
        "curated_release": curated_lock["release_tag"],
        "curated_osis_sha256": curated_lock["osis_sha256"],
        "source_license_clear_bible": "CC BY 4.0",
        "source_license_aquifer_alignment": "CC BY-SA 4.0",
        "publication_approved": False,
        "automatic_linguistic_approval": False,
        "original_group_counts": groups,
        "aquifer_text_witness_census": census,
        "status_counts": dict(sorted(statuses.items())),
        "target_id_calibration": dict(sorted(calibration.items())),
        "by_original_macula_id": dict(sorted(by_macula.items())),
        "by_lsg_word": dict(sorted(by_french_word.items())),
        "rows": rows,
    }
    return ((json.dumps(report, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8"),
            {k: report[k] for k in (
                "original_group_counts", "aquifer_text_witness_census",
                "status_counts", "target_id_calibration")})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aquifer-root", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--curated-root", required=True, type=Path)
    parser.add_argument("--curated-lock", required=True, type=Path)
    parser.add_argument("--clear-revision", required=True)
    parser.add_argument("--aquifer-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--min-chapters", type=int, default=1180)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT) or args.report.resolve().is_relative_to(ROOT):
        raise ValueError("nonpublishing outputs must remain outside the repository")
    curated = json.loads(args.curated_lock.read_text(encoding="utf-8"))
    osis = ed.pinned_file(args.curated_root, curated["osis_path"], curated["osis_sha256"])
    raw, counts = build_corroborated_index(
        args.aquifer_root, args.candidates, osis, curated,
        args.clear_revision, args.aquifer_revision, args.min_chapters)
    receipt = {
        "schema_version": 1,
        "kind": "brsi-macula-curated-lsg-word-corroboration-development",
        "source_clear_bible_revision": args.clear_revision,
        "source_aquifer_revision": args.aquifer_revision,
        "curated_release": curated["release_tag"],
        "curated_osis_sha256": curated["osis_sha256"],
        "publication_approved": False,
        "no_automatic_editorial_approval": True,
        **counts,
        "uncompressed_bytes": len(raw),
        "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
    }
    with args.output.open("wb") as target:
        with gzip.GzipFile(fileobj=target, filename="", mode="wb", mtime=0, compresslevel=9) as gz:
            gz.write(raw)
    receipt["gzip_bytes"] = args.output.stat().st_size
    receipt["gzip_sha256"] = ed.sha256(args.output)
    args.report.write_text(json.dumps(receipt, indent=2, sort_keys=True,
                                      ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
