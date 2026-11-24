#!/usr/bin/env python3
"""Nonpublishing phrase-boundary hypotheses between existing MACULA-LSG anchors.

This is a conservative *localization* baseline, NOT semantic translation
approval. Existing original-token/French-word pairs are immutable witnesses.
Two correctly ordered anchors can bound a missing original-token group and a
French phrase. This does NOT mean every source token translates every French
word in that phrase. A word may be grammatically unpaired.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_helper(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


lexical = load_helper("audit_macula_lsg_contextual_lexical_pilot.py",
                      "brsi_existing_lexical_pilot")
sampler = load_helper("sample_macula_lsg_semantic_review.py",
                      "brsi_existing_review_sampler")
bridge = lexical.bridge

# Predeclared, not optimized on blind outcomes.
MAX_ORIGINAL_GROUP = 6
MAX_FRENCH_SPAN = 8


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pinned_index(path: Path, lock: dict) -> tuple[dict, str]:
    packed = path.read_bytes()
    digest = sha256(packed)
    if digest != lock["gzip_sha256"]:
        raise ValueError("original MACULA-LSG development index SHA-256 mismatch")
    index = json.loads(gzip.decompress(packed))
    for field, other in (
        ("source_clear_bible_revision", "source_clear_bible_revision"),
        ("source_aquifer_revision", "source_aquifer_revision"),
        ("curated_osis_sha256", "curated_osis_sha256"),
    ):
        if index[field] != lock[other]:
            raise ValueError("source or authored French edition identity changed")
    if len(index["by_original_macula_id"]) != 607217:
        raise ValueError("full original MACULA identity census changed")
    return index, digest


def original_verses(index: dict) -> dict[str, list[str]]:
    verses = defaultdict(list)
    for source in index["by_original_macula_id"]:
        canon, _book, verse = sampler.coordinates(source)
        verses[verse].append(source)
    for sources in verses.values():
        sources.sort()
    return verses


def exact_anchor(index: dict, source: str, *,
                 hidden_source: str | None = None,
                 hidden_french_word: str | None = None) -> tuple[str, int] | None:
    """Use direct Clear.Bible NT word evidence or explicitly lower-tier OT.

    Source IDs and word IDs must use the same verse. Hiding the evaluated
    source *and every source sharing its gold word* prevents answer leakage.
    """
    if source == hidden_source:
        return None
    canon, _book, verse = sampler.coordinates(source)
    found = lexical.one_word_id(index, source, direct_only=(canon == "nt"))
    if not found or found == hidden_french_word:
        return None
    target_verse, sep, raw = found.partition(":")
    if not sep or target_verse != verse or not raw.isdecimal():
        return None
    ordinal = int(raw)
    if ordinal < 1:
        return None
    return found, ordinal


def bounded_groups_for_verse(index: dict, sources: list[str],
                             word_count: int, *,
                             hidden_source: str | None = None,
                             hidden_french_word: str | None = None,
                             max_original_group: int = MAX_ORIGINAL_GROUP,
                             max_french_span: int = MAX_FRENCH_SPAN
                             ) -> list[dict]:
    """Only bracket contiguous unlinked original units and French spans.

    A crossing/repeated/outside anchor, mismatched reference, an existing
    source link inside a gap or excessive span forces abstention. Never
    convert a bracket into independent word-to-word equivalences.
    """
    if not sources or word_count < 1 or max_original_group < 1 or max_french_span < 1:
        return []
    verse = sampler.coordinates(sources[0])[2]
    if len(set(sources)) != len(sources) or sources != sorted(sources) or any(
            sampler.coordinates(s)[2] != verse for s in sources):
        raise ValueError("source group has unsorted, duplicated or cross-verse IDs")
    anchors = []
    for i, source in enumerate(sources):
        result = exact_anchor(index, source, hidden_source=hidden_source,
                              hidden_french_word=hidden_french_word)
        if result is not None:
            word, ordinal = result
            if ordinal > word_count:
                raise ValueError("anchor points beyond exact authored French verse")
            anchors.append((i, source, word, ordinal))
    # Repeated positions among distinct source anchors are legitimate 2:1
    # translations, but not safe evidence for unique phrase boundaries.
    occupied = Counter(a[3] for a in anchors)
    unresolved = index["unlinked_cause_by_original_macula_id"]
    proposals = []
    for left, right in zip(anchors, anchors[1:]):
        li, ls, lw, lp = left
        ri, rs, rw, rp = right
        middle = sources[li + 1:ri]
        span_size = rp - lp - 1
        if (not middle or len(middle) > max_original_group or
                not 1 <= span_size <= max_french_span or
                occupied[lp] != 1 or occupied[rp] != 1):
            continue
        if any(s not in unresolved and s != hidden_source for s in middle):
            continue
        # Another source anchor elsewhere in this verse may point into the
        # French interval out of source order; its presence invalidates a
        # simple bracket as a unique localization hypothesis.
        if any(lp < anchor[3] < rp for anchor in anchors):
            continue
        target_words = [f"{verse}:{j}" for j in range(lp + 1, rp)]
        if not target_words:
            continue
        proposals.append({
            "original_macula_ids": middle,
            "lsg_word_ids": target_words,
            "left_anchor_original_macula_id": ls,
            "left_anchor_lsg_word_id": lw,
            "right_anchor_original_macula_id": rs,
            "right_anchor_lsg_word_id": rw,
            "source_verse": verse,
            "anchor_tier": ("clear_bible_direct_nt_word"
                            if sources[0].startswith("n")
                            else "aquifer_surface_attested_ot_candidate"),
            "evidence_kind": "ordered_neighbor_phrase_bracket_only",
            "semantic_equivalence_approved": False,
            "source_words_individually_linked": False,
            "unpaired_grammar_not_disproved": True,
            "publication_authorized": False,
        })
    return proposals


def metrics(gold: dict[str, str], predictions: dict[str, dict]) -> dict:
    correct_contains = exact_singleton = wrong = multi_contains = 0
    widths = Counter()
    for source, value in predictions.items():
        span = value["lsg_word_ids"]
        widths[len(span)] += 1
        if gold[source] in span:
            correct_contains += 1
            if len(span) == 1:
                exact_singleton += 1
            else:
                multi_contains += 1
        else:
            wrong += 1
    count = len(predictions)
    return {
        "cases": len(gold),
        "proposed_original_ids": count,
        "abstained_original_ids": len(gold) - count,
        "target_word_inside_proposed_bracket": correct_contains,
        "target_word_outside_proposed_bracket": wrong,
        "exact_single_word_target": exact_singleton,
        "multiword_bracket_contains_target": multi_contains,
        "bracket_containment_precision": round(correct_contains / count, 5)
        if count else 0.0,
        "original_id_coverage": round(count / len(gold), 5) if gold else 0.0,
        "bracket_width_distribution": dict(sorted(widths.items())),
    }


def analyze(index: dict, reviewed_cases: list[dict], nt_pivot: dict,
            authored: dict[str, str]) -> tuple[dict, list[dict]]:
    by_verse = original_verses(index)
    word_counts = {}

    def count(verse: str) -> int:
        if verse not in word_counts:
            word_counts[verse] = len(bridge.word_tokens(authored[verse])) if verse in authored else 0
        return word_counts[verse]

    unresolved = index["unlinked_cause_by_original_macula_id"]
    total_counts = Counter(unresolved.values())
    full_by_source: dict[str, dict] = {}
    all_groups = []
    for verse, sources in sorted(by_verse.items()):
        if not any(s in unresolved for s in sources):
            continue
        for group in bounded_groups_for_verse(index, sources, count(verse)):
            # Each unresolved source may be represented in a single
            # original-neighbor gap. Reject duplicates instead of arbitrary
            # last-write-wins.
            for source in group["original_macula_ids"]:
                if source in full_by_source:
                    raise ValueError("overlapping phrase-bracket source groups")
                full_by_source[source] = group
            all_groups.append(group)
    totals = Counter()
    sample = Counter()
    sample_by_canon = Counter()
    for source, reason in unresolved.items():
        if source in full_by_source:
            totals[reason] += 1
    # The review sample itself is never treated as human-annotated gold.
    for case in reviewed_cases:
        source = case["original_macula_id"]
        if source not in unresolved or unresolved[source] != case["source_cause"]:
            raise ValueError("review sample changed original category identity")
        if source in full_by_source:
            sample[case["source_cause"]] += 1
            sample_by_canon[case["canon"]] += 1

    gold = lexical.select_blind_gold(index, nt_pivot, authored, n=2000)
    chosen = sorted(gold, key=lexical.stable_key)
    gold_parts = [dict((s, gold[s]) for s in chosen[:1000]),
                  dict((s, gold[s]) for s in chosen[1000:])]
    evaluations = []
    for half in gold_parts:
        found = {}
        for source, target in half.items():
            verse = source[1:9]
            # All direct word evidence in this target word is hidden, not
            # just the source token selected as the gold answer.
            candidates = bounded_groups_for_verse(
                index, by_verse[verse], count(verse),
                hidden_source=source, hidden_french_word=target)
            for group in candidates:
                if source in group["original_macula_ids"]:
                    found[source] = group
                    break
        evaluations.append(metrics(half, found))

    breakdown = {
        reason: {"unlinked_original_ids": total_counts[reason],
                 "bracketed_original_ids": totals[reason],
                 "abstained_original_ids": total_counts[reason] - totals[reason],
                 "sample_original_ids": 500,
                 "sample_bracketed_original_ids": sample[reason]}
        for reason in sampler.STRATA
    }
    counts = Counter()
    for group in all_groups:
        counts["brackets"] += 1
        counts["bracketed_original_ids"] += len(group["original_macula_ids"])
        if len(group["lsg_word_ids"]) == 1:
            counts["one_french_word_brackets"] += 1
        else:
            counts["multiword_french_brackets"] += 1
        if len(group["original_macula_ids"]) > 1:
            counts["multiple_original_ids_brackets"] += 1
    if sum(totals.values()) != counts["bracketed_original_ids"]:
        raise ValueError("source-bracket cause accounting inconsistent")
    report = {
        "kind": "brsi-macula-lsg-phrase-bracket-nonpublishing-research",
        "schema_version": 1,
        "method": "strict_adjacent_existing_word_anchors_bracket_only",
        "max_original_group": MAX_ORIGINAL_GROUP,
        "max_french_span": MAX_FRENCH_SPAN,
        "reviewed_gold_cases": 0,
        "automatically_approved_new_links": 0,
        "source_originals_modified": False,
        "source_text_modified": False,
        "publication_authorized": False,
        "source_word_candidates_only": True,
        "nt_anchor_grade": "direct_clear_bible_word_position_not_editorially_verified",
        "ot_anchor_grade": "aquifer_source_to_french_candidate_not_independently_gold_verified",
        "unlinked_source_original_ids": len(unresolved),
        "full_corpus_brackets": dict(sorted(counts.items())),
        "by_unlinked_source_cause": breakdown,
        "review_sample_by_canon_with_bracket": dict(sorted(sample_by_canon.items())),
        "masked_direct_nt_2k_gold": {
            "design": "2000_distinct_NT_verses_with_masked_source_and_all_same_word_anchors",
            "calibration_half": evaluations[0],
            "independent_reporting_half": evaluations[1],
            "limitation": "bracket containment is not semantic correctness or exact phrase-boundary gold",
        },
    }
    return report, all_groups


def compressed_private(data: dict) -> bytes:
    payload = (json.dumps(data, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0,
                       compresslevel=9) as stream:
        stream.write(payload)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original-index", "correspondence-lock", "semantic-sample-lock",
                 "curated-lock", "curated-root", "pivot-lock", "pivot-nt",
                 "report", "private-brackets"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for path in (args.report, args.private_brackets):
        if path.resolve().is_relative_to(ROOT):
            raise ValueError("experimental reports and bracket candidates must stay outside Git")
    if args.report.resolve() == args.private_brackets.resolve():
        raise ValueError("report and private phrase data require different output paths")
    lock = json.loads(args.correspondence_lock.read_text(encoding="utf-8"))
    index, index_sha = pinned_index(args.original_index, lock)
    sample_lock = json.loads(args.semantic_sample_lock.read_text(encoding="utf-8"))
    sample_raw, _ = sampler.render(index, lock, index_sha, per_stratum=500)
    if (sha256(sample_raw) != sample_lock["private_unreviewed_cases_sha256"]
            or sample_lock["source_index_gzip_sha256"] != index_sha
            or sample_lock["case_count"] != 2000):
        raise ValueError("semantic review sample differs from frozen source-locked receipt")
    cases = json.loads(sample_raw)["cases"]
    edition = json.loads(args.curated_lock.read_text(encoding="utf-8"))
    if edition["osis_sha256"] != index["curated_osis_sha256"]:
        raise ValueError("curated authored OSIS revision changed")
    osis = bridge.ed.pinned_file(args.curated_root, edition["osis_path"],
                                 edition["osis_sha256"])
    authored = bridge.ed.read_osis(osis)
    pivot = json.loads(args.pivot_lock.read_text(encoding="utf-8"))
    nt_pivot, _ = lexical.pivot_source(
        args.pivot_nt, "nt", pivot["sources"]["nt"]["sha256"])
    report, groups = analyze(index, cases, nt_pivot, authored)
    report["source_index_gzip_sha256"] = index_sha
    report["original_clear_bible_revision"] = lock["source_clear_bible_revision"]
    report["original_aquifer_revision"] = lock["source_aquifer_revision"]
    report["curated_osis_sha256"] = lock["curated_osis_sha256"]
    report["semantic_sample_sha256"] = sample_lock["private_unreviewed_cases_sha256"]
    private = compressed_private({
        "kind": "brsi-private-unapproved-grouped-phrase-brackets",
        "source_index_gzip_sha256": index_sha,
        "brackets": groups,
        "automatic_approval": False,
        "publication_authorized": False,
    })
    report["private_brackets_sha256"] = sha256(private)
    report["private_brackets_bytes"] = len(private)
    args.private_brackets.write_bytes(private)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print("BRSI_MACULA_PHRASE_BRACKET_SUMMARY",
          json.dumps({"counts": report["full_corpus_brackets"],
                      "masked_nt": report["masked_direct_nt_2k_gold"],
                      "private_sha256": report["private_brackets_sha256"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
