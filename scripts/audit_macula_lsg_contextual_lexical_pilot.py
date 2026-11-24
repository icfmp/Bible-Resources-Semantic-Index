#!/usr/bin/env python3
"""Nonpublishing MACULA→LSG contextual-lexical candidate experiment.

This script does NOT endorse a Greek/Hebrew translation, modify an
existing word link, assign a grammatical equivalence, or rewrite Scripture.
Train a source-lemma→actually observed French surface distribution only
from retained source-index records. Evaluate *blind* against 2,000 held-out
single-token, directly text-attested NT Clear.Bible links, excluding every
evaluation verse from all training. Report held-out precision, attempted
coverage, and four-stratum unresolved-source candidate cohorts separately.

This is a lexical-semantic baseline with verse-context filtering, not a
claim of contextual Greek/Hebrew meaning disambiguation or a neural model.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "brsi_lexical_pilot_bridge", ROOT / "scripts" /
    "build_curated_lsg_word_correspondence.py")
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)

SEED = "brsi-2026-macula-semantic-2000-v1"
THRESHOLDS = ((3, 0.5), (5, 0.6), (8, 0.7), (12, 0.8),
              (20, 0.85), (30, 0.9), (50, 0.95))
STRATA = (
    "aquifer_explicit_non_equivalent_source",
    "other_part_of_same_original_word_has_link",
    "aquifer_record_source_with_no_uniquely_located_french_word",
    "not_present_in_aquifer_source_alignment_records",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def stable_key(value: str) -> str:
    return hashlib.sha256((SEED + ":" + value).encode("utf-8")).hexdigest()


def pivot_source(path: Path, canon: str, expected_sha: str
                 ) -> tuple[dict[str, tuple[str, str]], dict]:
    if sha256_file(path) != expected_sha:
        raise ValueError("MACULA original pivot source SHA-256 differs from locked revision")
    words = {}
    total = pos_present = blank_lemma = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or not {"xml:id", "lemma"} <= set(reader.fieldnames):
            raise ValueError("MACULA original TSV lacks exact ID or lemma columns")
        pos_field = next((f for f in ("sp", "pos", "partOfSpeech", "part_of_speech")
                          if f in reader.fieldnames), None)
        for row in reader:
            total += 1
            raw = (row.get("xml:id") or "").strip()
            lemma = norm(row.get("lemma") or "")
            if not lemma:
                blank_lemma += 1
            pos = norm(row.get(pos_field) or "") if pos_field else ""
            if pos:
                pos_present += 1
            if not raw:
                raise ValueError("empty MACULA original token ID")
            prefix = "n" if canon == "nt" else "o"
            key = raw if raw.startswith(prefix) else prefix + raw
            if key in words:
                raise ValueError("duplicate original MACULA token ID")
            words[key] = (lemma, pos)
    return words, {"tokens": total, "blank_lemma": blank_lemma,
                   "pos_column": pos_field, "pos_available": pos_present}


def one_word_id(index: dict, source_id: str, *,
                direct_only: bool = False) -> str | None:
    positions = set()
    for idx in index["by_original_macula_id"].get(source_id, []):
        row = index["rows"][idx]
        if direct_only and not (
                row["status"].startswith("clear_bible_direct_word")
                and row["canon"] == "nt"
                and len(row["original_macula_ids"]) == 1):
            continue
        positions.update(row["word_ids"])
    if len(positions) != 1:
        return None
    word_id = next(iter(positions))
    return word_id if word_id.partition(":")[0] == source_id[1:9] else None


def select_blind_gold(index: dict, pivot_nt: dict,
                      authored: dict[str, str], n: int = 2000
                      ) -> dict[str, str]:
    """Take 1 source word per verse; no shared verse leaks into training."""
    by_verse = defaultdict(list)
    for source in index["by_original_macula_id"]:
        if not source.startswith("n") or source not in pivot_nt:
            continue
        if not pivot_nt[source][0]:
            continue
        word = one_word_id(index, source, direct_only=True)
        if word is not None and word.partition(":")[0] in authored:
            by_verse[source[1:9]].append((source, word))
    verse_list = sorted(by_verse, key=stable_key)
    chosen = {}
    for verse in verse_list:
        pairs = sorted(by_verse[verse], key=lambda p: stable_key(p[0]))
        if pairs:
            chosen[pairs[0][0]] = pairs[0][1]
        if len(chosen) >= n:
            break
    if len(chosen) != n:
        raise ValueError("not enough independent NT verses for blind sample")
    if len({source[1:9] for source in chosen}) != n:
        raise ValueError("evaluation leakage: repeated original source verse")
    return chosen


def words_in_verse(verse: str, authored: dict[str, str],
                   cache: dict[str, list[str]]) -> list[str]:
    if verse not in cache:
        if verse not in authored:
            return []
        cache[verse] = [word for word, _, _ in bridge.word_tokens(authored[verse])]
    return cache[verse]


def lexical_buckets(index: dict, pivots: dict, authored: dict,
                    holdout_verses: set[str]) -> tuple[dict, dict]:
    """Independent verse evidence counts, with direct NT gold prioritized.

    Every unique source lemma/French surface/verse contributes at most
    once; correlated grouped source IDs do not inflate corpus support.
    Hebrew OT Aquifer links remain model-assisted lexical hypotheses.
    """
    inventory = {}
    full = defaultdict(lambda: defaultdict(set))
    with_pos = defaultdict(lambda: defaultdict(set))
    stats = Counter()
    for source in index["by_original_macula_id"]:
        canon = "nt" if source.startswith("n") else "ot"
        if source[1:9] in holdout_verses:
            continue
        original = pivots[canon].get(source)
        if not original:
            stats["source_missing_original_pivot"] += 1
            continue
        lemma, pos = original
        if not lemma:
            stats["source_without_lemma"] += 1
            continue
        word_id = one_word_id(index, source, direct_only=(canon == "nt"))
        if word_id is None:
            continue
        verse, _, ordinal = word_id.partition(":")
        actual = words_in_verse(verse, authored, inventory)
        try:
            word_index = int(ordinal) - 1
            surface = norm(actual[word_index])
        except (ValueError, IndexError):
            raise ValueError("original source candidate has invalid authorial LSG coordinate")
        if not surface:
            continue
        full[(canon, lemma)][surface].add(verse)
        if pos:
            with_pos[(canon, lemma, pos)][surface].add(verse)
        stats[canon + "_original_training_source_ids"] += 1
    # The same lemma may legitimately map to many distinct French words.
    return ({name: {key: {w: len(verses) for w, verses in words.items()}
                    for key, words in source.items()}
             for name, source in (("lemma", full), ("lemma_pos", with_pos))},
            dict(sorted(stats.items())))


def predict(source_id: str, pivot: dict,
            authored: dict[str, str], cache: dict,
            distributions: dict) -> dict | None:
    canon = "nt" if source_id.startswith("n") else "ot"
    word = pivot.get(source_id)
    if not word or not word[0]:
        return None
    lemma, pos = word
    basic = distributions["lemma"].get((canon, lemma), {})
    refined = distributions["lemma_pos"].get((canon, lemma, pos), {}) if pos else {}
    # Do not prefer a morphology-specific bucket supported by only one
    # isolated verse: it can easily encode an accidental word coincidence.
    counts = refined if sum(refined.values()) >= 8 else basic
    if not counts:
        return None
    verse = source_id[1:9]
    words = words_in_verse(verse, authored, cache)
    if not words:
        return None
    normalized = [norm(surface) for surface in words]
    frequencies = Counter(normalized)
    options = [(counts[value], i, value) for i, value in enumerate(normalized)
               if frequencies[value] == 1 and value in counts]
    if not options:
        return None
    options.sort(key=lambda v: (-v[0], v[1]))
    support, location, matched = options[0]
    if len(options) > 1 and support == options[1][0]:
        return None
    total = sum(counts.values())
    if total <= 0 or support <= 0:
        return None
    second_support = options[1][0] if len(options) > 1 else 0
    return {
        "source_id": source_id,
        "word_id": f"{verse}:{location + 1}",
        "word_sha256": hashlib.sha256(words[location].encode("utf-8")).hexdigest(),
        "lemma_sha256": hashlib.sha256(lemma.encode("utf-8")).hexdigest(),
        "pivot_morphology_used": bool(refined and counts is refined),
        "support_independent_source_verses": support,
        "share": round(support / total, 6),
        "margin": round((support - second_support) / total, 6),
        "candidate_only": True,
        "automatic_linguistic_approval": False,
    }


def qualifies(proposal: dict | None, threshold: tuple[int, float]) -> bool:
    return bool(proposal and
                proposal["support_independent_source_verses"] >= threshold[0]
                and proposal["share"] + 1e-8 >= threshold[1]
                and proposal["margin"] >= 0.15)


def metrics(gold: dict[str, str], predicted: dict,
            threshold: tuple[int, float] | None) -> dict:
    chosen = [(source, prediction) for source, prediction in predicted.items()
              if prediction and (threshold is None or qualifies(prediction, threshold))]
    right = sum(prediction["word_id"] == gold[source]
                for source, prediction in chosen)
    n = len(chosen)
    p = right / n if n else 0.
    # Wilson 95% lower bound, to expose sample-size uncertainty.
    z = 1.96
    denominator = 1 + z*z/n if n else 1
    lower = ((p + z*z/(2*n) - z*math.sqrt(
        p*(1-p)/n+z*z/(4*n*n))) / denominator) if n else 0.
    return {"gold": len(gold), "proposed": n, "correct": right,
            "incorrect": n-right,
            "precision": round(p, 5),
            "precision_wilson95_lower": round(lower, 5),
            "coverage": round(n/len(gold), 5) if gold else 0.}


def pilot(index: dict, pivot_sources: dict, authored: dict,
          *, validation_words: int = 2000, preview_per_stratum: int = 500
          ) -> tuple[dict, list[dict]]:
    if not 1 <= validation_words <= 5000 or validation_words % 2:
        raise ValueError("blind sample must be even and between 2 and 5000")
    gold = select_blind_gold(index, pivot_sources["nt"], authored, validation_words)
    heldout_verses = {source[1:9] for source in gold}
    buckets, train_stats = lexical_buckets(
        index, pivot_sources, authored, heldout_verses)
    inventory = {}
    ordered = sorted(gold, key=stable_key)
    half = validation_words // 2
    cal_sources = ordered[:half]
    validation_sources = ordered[half:]
    cal_gold = {s:gold[s] for s in cal_sources}
    val_gold = {s:gold[s] for s in validation_sources}
    cal = {s:predict(s, pivot_sources["nt"], authored, inventory, buckets)
           for s in cal_sources}
    val = {s:predict(s, pivot_sources["nt"], authored, inventory, buckets)
           for s in validation_sources}
    calibration_grid = []
    for rule in THRESHOLDS:
        result = metrics(cal_gold, cal, rule)
        calibration_grid.append({"min_source_verses": rule[0],
                                 "min_lemma_share": rule[1], **result})
    plausible = [(r["proposed"], (r["min_source_verses"], r["min_lemma_share"]))
                 for r in calibration_grid
                 if r["proposed"] >= 30 and r["precision"] >= .97]
    selected = sorted(plausible, key=lambda x: (-x[0], x[1]))[0][1] if plausible else None
    evaluation = metrics(val_gold, val, selected) if selected else metrics(val_gold, {}, None)
    # Selection was done on calibration only; the 1,000 verse-disjoint
    # validation links must independently clear a meaningful threshold.
    heldout_ok = (selected is not None and evaluation["proposed"] >= 25
                  and evaluation["precision"] >= .95)
    limits = selected if heldout_ok else (3, .5)
    unresolved = index["unlinked_cause_by_original_macula_id"]
    counts = defaultdict(Counter)
    preview = defaultdict(list)
    proposals = []
    for source, reason in sorted(unresolved.items()):
        canon = "nt" if source.startswith("n") else "ot"
        guess = predict(source, pivot_sources[canon], authored, inventory, buckets)
        counts[reason]["total"] += 1
        if source not in pivot_sources[canon]:
            counts[reason]["no_exact_original_macula_id"] += 1
        elif not pivot_sources[canon][source][0]:
            counts[reason]["no_source_lemma"] += 1
        if guess is None:
            continue
        counts[reason]["non_unique_or_unattested_candidate"] += 1
        if qualifies(guess, (3, .5)):
            counts[reason]["exploratory_candidate"] += 1
            if heldout_ok and qualifies(guess, selected):
                counts[reason]["heldout_qualified_candidate"] += 1
            proposal = {**guess, "source_cause": reason,
                        "heldout_qualified": bool(
                            heldout_ok and qualifies(guess, selected)),
                        "human_reviewed": False}
            proposals.append(proposal)
            if len(preview[reason]) < preview_per_stratum:
                preview[reason].append(proposal)
    if sum(v["total"] for v in counts.values()) != len(unresolved):
        raise ValueError("original unlinked MACULA corpus not completely partitioned")
    if set(counts) != set(STRATA):
        raise ValueError("source diagnostic categories unexpected")
    selected_sample = []
    # Source-key ordering is stable and complete. Select each audit stratum
    # by seeded hash, so the preview cannot be biased by book order.
    for stratum in STRATA:
        subset = sorted((p for p in proposals if p["source_cause"] == stratum),
                        key=lambda p: stable_key(p["source_id"]))
        selected_sample.extend(subset[:preview_per_stratum])
    # Keep every unlinked *source ID* represented in the private census,
    # but only emit actual hypotheses in the private candidates.
    report = {
        "kind": "brsi-semantic-lexical-context-pilot-nonpublishing",
        "schema_version": 1,
        "training_includes_unreviewed_ot_aquifer_hypotheses": True,
        "nt_gold": "direct_unique_original_clear_bible_nt_word_attestation",
        "nt_gold_verses_held_out_from_all_lexical_training": len(heldout_verses),
        "nt_gold_size": len(gold),
        "training": train_stats,
        "lexicon_keys": {
            "lemma": len(buckets["lemma"]),
            "lemma_with_morphology": len(buckets["lemma_pos"])},
        "calibration_half": {"size": len(cal_gold),
                             "all_predictions": metrics(cal_gold, cal, None),
                             "threshold_grid": calibration_grid},
        "blind_validation_half": {
            "size": len(val_gold),
            "all_predictions": metrics(val_gold, val, None),
            "selected_threshold_from_calibration": (
                {"min_support": selected[0], "min_share": selected[1]}
                if selected else None),
            "threshold_metrics": evaluation,
            "pilot_precision_gate_passed": heldout_ok},
        "unresolved_original_source_by_cause": {
            k: dict(sorted(v.items())) for k,v in sorted(counts.items())},
        "unresolved_original_source_count": len(unresolved),
        "all_exploratory_candidate_count": len(proposals),
        "audit_preview_max_sources": preview_per_stratum * len(STRATA),
        "actual_audit_preview_sources": len(selected_sample),
        "none_of_the_original_macula_ids_rewritten": True,
        "no_new_source_word_link_accepted": True,
        "semantic_translation_approved": False,
        "publication_authorized": False,
    }
    return report, proposals


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("original-index", "correspondence-lock", "pivot-lock",
                 "pivot-nt", "pivot-ot", "curated-root",
                 "curated-lock", "report", "private-candidates"):
        p.add_argument("--"+name, required=True, type=Path)
    p.add_argument("--blind-nt-gold-size", type=int, default=2000)
    args = p.parse_args()
    if args.report.resolve().is_relative_to(ROOT) or args.private_candidates.resolve().is_relative_to(ROOT):
        raise ValueError("private candidate and report output must remain outside repo")
    correspondence = json.loads(args.correspondence_lock.read_text(encoding="utf-8"))
    if sha256_file(args.original_index) != correspondence["gzip_sha256"]:
        raise ValueError("complete MACULA correspondence gzip does not match source lock")
    with gzip.open(args.original_index, "rt", encoding="utf-8") as stream:
        index = json.load(stream)
    if (index["source_clear_bible_revision"] != correspondence["source_clear_bible_revision"] or
        index["source_aquifer_revision"] != correspondence["source_aquifer_revision"] or
        index["curated_osis_sha256"] != correspondence["curated_osis_sha256"]):
        raise ValueError("MACULA source index source editions changed")
    pivot = json.loads(args.pivot_lock.read_text(encoding="utf-8"))
    pivots, pivot_stats = {}, {}
    for canon,path in (("nt",args.pivot_nt), ("ot",args.pivot_ot)):
        expected = pivot["sources"][canon]["sha256"]
        pivots[canon],pivot_stats[canon] = pivot_source(path,canon,expected)
    edition = json.loads(args.curated_lock.read_text(encoding="utf-8"))
    if edition["osis_sha256"] != index["curated_osis_sha256"]:
        raise ValueError("published LSG OSIS SHA differs from source corpus lock")
    osis = bridge.ed.pinned_file(args.curated_root, edition["osis_path"], edition["osis_sha256"])
    authored = bridge.ed.read_osis(osis)
    report, proposals = pilot(index, pivots, authored,
                              validation_words=args.blind_nt_gold_size)
    report["original_index_gzip_sha256"] = correspondence["gzip_sha256"]
    report["source_clear_bible_revision"] = index["source_clear_bible_revision"]
    report["source_aquifer_revision"] = index["source_aquifer_revision"]
    report["source_macula_pivot_revisions"] = {
        c:pivot["sources"][c]["revision"] for c in ("nt","ot")}
    report["original_macula_pivot_statistics"] = pivot_stats
    report["curated_osis_sha256"] = edition["osis_sha256"]
    # No Scripture text, original-language lemma text or French word
    # surfaces in the private detail; only original IDs, actual authored
    # positions, hashes and separately graded candidate scores.
    payload = (json.dumps(proposals, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"))+"\n").encode("utf-8")
    with args.private_candidates.open("wb") as file:
        with gzip.GzipFile(fileobj=file, mode="wb", filename="", mtime=0,
                           compresslevel=9) as out:
            out.write(payload)
    report["private_exploratory_candidate_gzip_sha256"] = sha256_file(args.private_candidates)
    report["private_exploratory_candidate_gzip_bytes"] = args.private_candidates.stat().st_size
    args.report.write_text(json.dumps(report, ensure_ascii=False,
                                     sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
