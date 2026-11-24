#!/usr/bin/env python3
"""Cross-check lexical MACULA guesses against independent LSG phrase anchors.

**Nonpublishing research:** A lemma-derived candidate cannot become a French
word link merely because it lies inside a phrase bracket. Both signals reuse
some original upstream alignment evidence; their agreement is NOT independent
human gold. The blind NT test masks the gold word and excludes *all 2,000
evaluation verses* from lexical training to measure localization errors.

No original, Scripture, source index, approved link or Bible app is changed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_phrase_consensus", ROOT / "scripts" /
    "audit_macula_lsg_phrase_brackets.py")
phrase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phrase)
lexical = phrase.lexical
sampler = phrase.sampler
bridge = phrase.bridge

# These thresholds are declared before independent reporting. Calibration
# alone can select a gate; no threshold is selected from the blind results.
THRESHOLDS = ((3, .5), (5, .6), (8, .7), (12, .8), (20, .85), (30, .9))
MODES = ("single_word_bracket", "any_bounded_phrase")
MIN_CALIBRATION_PROPOSALS = 25
MIN_CALIBRATION_PRECISION = .95
MIN_CALIBRATION_WILSON_LOWER = .84
MIN_BLIND_PROPOSALS = 25
MIN_BLIND_PRECISION = .95
MIN_BLIND_WILSON_LOWER = .84


def source_brackets(index: dict, authored: dict[str, str]) -> dict[str, dict]:
    """Read-only group-to-phrase candidates for the original unresolved set."""
    groups = {}
    unlinked = index["unlinked_cause_by_original_macula_id"]
    for verse, ids in sorted(phrase.original_verses(index).items()):
        if not any(word in unlinked for word in ids):
            continue
        count = len(bridge.word_tokens(authored[verse])) if verse in authored else 0
        for group in phrase.bounded_groups_for_verse(index, ids, count):
            for source in group["original_macula_ids"]:
                if source not in unlinked or source in groups:
                    raise ValueError("overlapping or already linked source phrase")
                groups[source] = group
    return groups


def consensus(source: str, guess: dict | None, group: dict | None
              ) -> dict | None:
    """Propose ONE word within ONE bounded source-group↔French phrase.

    A match is only a *candidate-location agreement*; the rest of a phrase
    may express multiple source units, grammar or nothing directly isolated.
    """
    if guess is None or group is None:
        return None
    candidate = guess.get("word_id")
    if not isinstance(candidate, str) or candidate not in group["lsg_word_ids"]:
        return None
    if source not in group["original_macula_ids"] or source[1:9] != group["source_verse"]:
        raise ValueError("cross-verse or non-member consensus group")
    if not all(word.startswith(source[1:9] + ":")
               for word in group["lsg_word_ids"]):
        raise ValueError("invalid authored LSG phrase reference")
    return {
        "source_id": source,
        "source_group_macula_ids": group["original_macula_ids"],
        "lsg_phrase_word_ids": group["lsg_word_ids"],
        "lemma_suggested_lsg_word_id": candidate,
        "word_sha256": guess["word_sha256"],
        "lemma_sha256": guess["lemma_sha256"],
        "support_independent_source_verses": guess["support_independent_source_verses"],
        "share": guess["share"],
        "margin": guess["margin"],
        "original_verse": source[1:9],
        "phrase_anchor_tier": group["anchor_tier"],
        "phrase_bracket_only": True,
        "lexical_candidate_only": True,
        "word_level_semantic_equivalence_proven": False,
        "group_phrase_semantic_equivalence_proven": False,
        "independently_human_reviewed": False,
        "source_words_individually_linked": False,
        "automatic_linguistic_approval": False,
        "publication_authorized": False,
    }



def constrained_lexical_candidate(
        source: str, original: dict,
        authored: dict[str, str], cache: dict,
        distributions: dict, group: dict | None) -> dict | None:
    """Search ONLY an anchored French phrase for attested lemma surfaces.

    The original linked-source lexicon is trained outside *all* evaluation
    verses; the phrase anchor constraints must independently locate its
    exact authored French words. No French word is invented. Do not
    coerce repeated surface forms, support ties or unpaired grammar.
    """
    if group is None:
        return None
    canon = "nt" if source.startswith("n") else "ot"
    data = original.get(source)
    if not data or not data[0]:
        return None
    lemma, pos = data
    basic = distributions["lemma"].get((canon, lemma), {})
    refined = distributions["lemma_pos"].get((canon, lemma, pos), {}) if pos else {}
    counts = refined if sum(refined.values()) >= 8 else basic
    if not counts:
        return None
    verse = source[1:9]
    if verse != group["source_verse"]:
        raise ValueError("anchored source and authored French verse disagree")
    french = lexical.words_in_verse(verse, authored, cache)
    if not french:
        return None
    possible = []
    frequency = Counter()
    for identifier in group["lsg_word_ids"]:
        bcv, colon, raw_ordinal = identifier.partition(":")
        if not colon or bcv != verse or not raw_ordinal.isdecimal():
            raise ValueError("phrase references non-authorial French verse/word")
        ordinal = int(raw_ordinal)
        if ordinal < 1 or ordinal > len(french):
            raise ValueError("original-source bracket points beyond French word text")
        surface = lexical.norm(french[ordinal-1])
        frequency[surface] += 1
        if surface in counts:
            possible.append((counts[surface], identifier, surface, ordinal))
    if not possible:
        return None
    possible.sort(key=lambda x: (-x[0], x[3]))
    top_support, word_id, text, ordinal = possible[0]
    # A tie or duplicate surface inside the same phrase has no unique
    # local target—even when the repeated word is unique elsewhere.
    if frequency[text] != 1 or (
            len(possible) > 1 and possible[1][0] == top_support):
        return None
    total = sum(counts.values())
    if total <= 0:
        return None
    second_support = possible[1][0] if len(possible) > 1 else 0
    guess = {
        "source_id": source, "word_id": word_id,
        "word_sha256": hashlib.sha256(
            french[ordinal-1].encode("utf-8")).hexdigest(),
        "lemma_sha256": hashlib.sha256(lemma.encode("utf-8")).hexdigest(),
        "support_independent_source_verses": top_support,
        "share": round(top_support / total, 6),
        "margin": round((top_support-second_support) / total, 6),
        "candidate_only": True,
        "automatic_linguistic_approval": False,
    }
    candidate = consensus(source, guess, group)
    if candidate is not None:
        candidate["lexical_selection_restricted_to_bounded_phrase"] = True
        candidate["word_level_semantic_equivalence_proven"] = False
    return candidate


def eligible(item: dict | None, threshold: tuple[int, float],
             mode: str) -> bool:
    if mode not in MODES:
        raise ValueError("unknown declared consensus mode")
    if not item:
        return False
    if mode == "single_word_bracket" and len(item["lsg_phrase_word_ids"]) != 1:
        return False
    return lexical.qualifies(item, threshold)


def error_metrics(gold: dict[str, str], guesses: dict[str, dict | None],
                  threshold: tuple[int, float], mode: str) -> dict:
    if set(guesses) != set(gold):
        raise ValueError("blind gold case set changed or leaked")
    selected = {
        source: suggestion for source, suggestion in guesses.items()
        if eligible(suggestion, threshold, mode)}
    attempted = len(selected)
    accurate_word = sum(
        gold[source] == suggestion["lemma_suggested_lsg_word_id"]
        for source, suggestion in selected.items())
    included = sum(
        gold[source] in suggestion["lsg_phrase_word_ids"]
        for source, suggestion in selected.items())
    precise = accurate_word / attempted if attempted else 0.
    # Conventional Wilson95 is reported only for held-out, distinct NT
    # source verses (not for dense correlated original-token samples).
    import math
    z = 1.96
    denom = 1+z*z/attempted if attempted else 1
    lower = ((precise + z*z/(2*attempted) - z*math.sqrt(
        precise*(1-precise)/attempted+z*z/(4*attempted*attempted))) /
        denom) if attempted else 0.
    return {
        "cases": len(gold),
        "attempted": attempted,
        "word_exact_correct": accurate_word,
        "word_exact_wrong": attempted - accurate_word,
        "phrase_contains_gold_word": included,
        "phrase_contains_gold_but_lemma_word_wrong": included - accurate_word,
        "phrase_excludes_gold_word": attempted - included,
        "abstained": len(gold) - attempted,
        "exact_word_precision": round(precise, 5),
        "wilson95_lower": round(lower, 5),
        "attempted_case_coverage": round(attempted/len(gold), 5) if gold else 0.,
        "not_independent_phrase_semantic_accuracy": True,
    }


def frozen_threshold(cal: dict[str, str], candidates: dict[str, dict | None]
                     ) -> tuple[dict | None, list[dict]]:
    grid = []
    suitable = []
    for mode in MODES:
        for threshold in THRESHOLDS:
            result = error_metrics(cal, candidates, threshold, mode)
            grid.append({"mode": mode, "min_source_verses": threshold[0],
                         "min_lemma_share": threshold[1], **result})
            if (result["attempted"] >= MIN_CALIBRATION_PROPOSALS and
                result["exact_word_precision"] >= MIN_CALIBRATION_PRECISION and
                result["wilson95_lower"] >= MIN_CALIBRATION_WILSON_LOWER):
                suitable.append((result["attempted"], result["wilson95_lower"],
                                 mode, threshold))
    if not suitable:
        return None, grid
    # Greedy maximize diagnostic coverage, tie-break with Wilson lower bound.
    # Entire selection is done on calibration, no blind result is examined.
    selected = sorted(suitable, key=lambda t: (-t[0], -t[1], t[2], t[3]))[0]
    return {"mode": selected[2], "min_source_verses": selected[3][0],
            "min_lemma_share": selected[3][1]}, grid


def calibrate(index: dict, pivots: dict, authored: dict[str, str],
              gold: dict[str, str], buckets: dict
              ) -> tuple[dict, dict]:
    if len(gold) != 2000 or len({s[1:9] for s in gold}) != 2000:
        raise ValueError("holdout must be 2000 independent original source verses")
    verses = phrase.original_verses(index)
    order = sorted(gold, key=lexical.stable_key)
    half = len(order)//2
    eval_parts = []
    eval_parts_constrained = []
    cached = {}
    for selected in (order[:half], order[half:]):
        answers = {source:gold[source] for source in selected}
        predictions = {}
        conditioned = {}
        for source in selected:
            verse = source[1:9]
            authored_count = (len(bridge.word_tokens(authored[verse]))
                              if verse in authored else 0)
            groups = phrase.bounded_groups_for_verse(
                index, verses[verse], authored_count,
                hidden_source=source, hidden_french_word=gold[source])
            relevant = [g for g in groups if source in g["original_macula_ids"]]
            if len(relevant) > 1:
                raise ValueError("multiple masked phrase candidates for one NT gold")
            guessed = lexical.predict(
                source, pivots["nt"], authored, cached, buckets)
            group = relevant[0] if relevant else None
            predictions[source] = consensus(source, guessed, group)
            conditioned[source] = constrained_lexical_candidate(
                source, pivots["nt"], authored, cached, buckets, group)
        eval_parts.append((answers, predictions))
        eval_parts_constrained.append((answers, conditioned))
    cal_gold, cal_guesses = eval_parts[0]
    blind_gold, blind_guesses = eval_parts[1]
    _cal_fixed, cal_constrained = eval_parts_constrained[0]
    _blind_fixed, blind_constrained = eval_parts_constrained[1]
    selected, grid = frozen_threshold(cal_gold, cal_guesses)
    if selected:
        threshold = (selected["min_source_verses"],
                     selected["min_lemma_share"])
        blind_metrics = error_metrics(blind_gold, blind_guesses,
                                      threshold, selected["mode"])
    else:
        blind_metrics = {
            "cases": len(blind_gold), "attempted": 0,
            "word_exact_correct": 0, "word_exact_wrong": 0,
            "phrase_contains_gold_word": 0,
            "phrase_contains_gold_but_lemma_word_wrong": 0,
            "phrase_excludes_gold_word": 0, "abstained": len(blind_gold),
            "exact_word_precision": 0., "wilson95_lower": 0.,
            "attempted_case_coverage": 0.,
            "not_independent_phrase_semantic_accuracy": True,
        }
    blind_gate = (
        selected is not None and
        blind_metrics["attempted"] >= MIN_BLIND_PROPOSALS and
        blind_metrics["exact_word_precision"] >= MIN_BLIND_PRECISION and
        blind_metrics["wilson95_lower"] >= MIN_BLIND_WILSON_LOWER)
    # All exploratory figures below are predeclared, not test-tuned:
    exploratory = (3, .5)
    compare = {
        mode: {
            "calibration_half": error_metrics(
                cal_gold, cal_guesses, exploratory, mode),
            "blind_half": error_metrics(
                blind_gold, blind_guesses, exploratory, mode)}
        for mode in MODES}
    # Challenger uses the *same masked NT cases*, never a different or
    # easier validation subset. Its lexical search is limited to the
    # anchored phrase rather than globally chosen before bracketing.
    challenger_selected, challenger_grid = frozen_threshold(
        cal_gold, cal_constrained)
    if challenger_selected:
        challenger_blind = error_metrics(
            blind_gold, blind_constrained,
            (challenger_selected["min_source_verses"],
             challenger_selected["min_lemma_share"]),
            challenger_selected["mode"])
    else:
        challenger_blind = error_metrics(
            blind_gold, {source:None for source in blind_gold},
            (3, .5), "any_bounded_phrase")
    challenger_gate = (
        challenger_selected is not None
        and challenger_blind["attempted"] >= MIN_BLIND_PROPOSALS
        and challenger_blind["exact_word_precision"] >= MIN_BLIND_PRECISION
        and challenger_blind["wilson95_lower"] >= MIN_BLIND_WILSON_LOWER)
    challenger_exploratory = {
        mode: {
            "calibration_half": error_metrics(
                cal_gold, cal_constrained, exploratory, mode),
            "blind_half": error_metrics(
                blind_gold, blind_constrained, exploratory, mode)}
        for mode in MODES}
    return {
        "2k_gold_design": "2000_distinct_NT_source_verses_all_excluded_from_lexical_training",
        "source_word_and_all_same_french_word_anchor_masked": True,
        "calibration_size": len(cal_gold),
        "blind_size": len(blind_gold),
        "predeclared_threshold_grid": grid,
        "selected_only_on_calibration": selected,
        "predeclared_exploratory_comparisons": compare,
        "blind_selected_threshold_metrics": blind_metrics,
        "blind_precision_gate_passed": blind_gate,
        "bracket_constrained_challenger": {
            "method": "source_lemma_attested_french_word_chosen_only_inside_bounded_phrase",
            "calibration_threshold_grid": challenger_grid,
            "selected_only_on_calibration": challenger_selected,
            "predeclared_exploratory_comparisons": challenger_exploratory,
            "blind_selected_threshold_metrics": challenger_blind,
            "blind_precision_gate_passed": challenger_gate,
            "no_semantic_approval": True,
        },
        "reuses_previously_reported_nt_verses_from_lexical_and_bracket_pilots": True,
        "not_a_fresh_prospectively_sealed_blind_gold_set": True,
        "disclaimer": (
            "Original NT positional pseudo-gold is independently source-attested; "
            "not linguistically reviewed phrase equivalence, no OT gold, "
            "no automatic production or editorial approval."),
    }, {"buckets": buckets}


def analyze(index: dict, pivots: dict, authored: dict[str, str],
            sampled_cases: list[dict]) -> tuple[dict, list[dict]]:
    gold = lexical.select_blind_gold(index, pivots["nt"], authored, n=2000)
    holdout_verses = {source[1:9] for source in gold}
    buckets, training = lexical.lexical_buckets(
        index, pivots, authored, holdout_verses)
    blind, _ = calibrate(index, pivots, authored, gold, buckets)
    bracket_by_source = source_brackets(index, authored)
    stats = defaultdict(Counter)
    samples = defaultdict(Counter)
    suggestions = []
    by_source = {}
    cached = {}
    unlinked = index["unlinked_cause_by_original_macula_id"]
    for source, reason in sorted(unlinked.items()):
        stats[reason]["total"] += 1
        bracket = bracket_by_source.get(source)
        if bracket is None:
            stats[reason]["no_bounded_phrase"] += 1
            continue
        stats[reason]["bounded_phrase_available"] += 1
        canon = "nt" if source.startswith("n") else "ot"
        guess = lexical.predict(source, pivots[canon], authored, cached, buckets)
        if guess is None:
            stats[reason]["no_lexical_suggestion"] += 1
            continue
        agreement = consensus(source, guess, bracket)
        if agreement is None:
            stats[reason]["lexical_phrase_disagree"] += 1
            continue
        stats[reason]["lexical_phrase_agree"] += 1
        if eligible(agreement, (3, .5), "any_bounded_phrase"):
            stats[reason]["predeclared_exploratory_agreement"] += 1
            if len(agreement["lsg_phrase_word_ids"]) == 1:
                stats[reason]["exploratory_singleword_phrase"] += 1
            else:
                stats[reason]["exploratory_multiword_phrase"] += 1
            data = {**agreement, "source_cause": reason,
                    "source_canon": canon, "candidate_only": True}
            suggestions.append(data)
            by_source[source] = data
        else:
            stats[reason]["below_predeclared_lexical_threshold"] += 1
    if sum(row["total"] for row in stats.values()) != len(unlinked):
        raise ValueError("unresolved source count differs from full pinned index")
    if set(stats) != set(sampler.STRATA):
        raise ValueError("unresolved cause classes disagree with frozen sample")
    for case in sampled_cases:
        source, cause = case["original_macula_id"], case["source_cause"]
        if unlinked.get(source) != cause:
            raise ValueError("sample case changed pinned stratum")
        samples[cause]["total"] += 1
        if source in by_source:
            samples[cause]["exploratory_agreement"] += 1
    if any(v["total"] != 500 for v in samples.values()):
        raise ValueError("review cohort is not evenly sampled across four strata")
    report = {
        "kind": "brsi-macula-lsg-lexical-and-phrase-consensus-negative-control",
        "schema_version": 1,
        "method": "lemma_lexical_candidate_inside_strict_ordered_anchored_french_phrase",
        "no_independent_phrase_semantics_demonstrated": True,
        "training_source_counts": training,
        "training_excludes_all_2k_heldout_nt_verses": True,
        "ot_training_uses_unreviewed_aquifer_candidates": True,
        "lexical_and_phrase_inputs_not_fully_independent": True,
        "source_coverage": {
            "full_original_macula_source_ids": len(index["by_original_macula_id"]),
            "baseline_ids_with_candidate_french_word": (
                len(index["by_original_macula_id"]) - len(unlinked)),
            "unresolved_original_macula_source_ids": len(unlinked),
            "bounded_original_source_ids": len(bracket_by_source),
            "lexical_phrase_exploratory_agreement_ids": len(suggestions),
            "new_linguistically_approved_original_ids": 0,
        },
        "four_unlinked_source_cause_counts": {
            cause: dict(sorted(stats[cause].items()))
            for cause in sampler.STRATA},
        "fixed_2k_reviewer_sample_counts": {
            cause: dict(sorted(samples[cause].items()))
            for cause in sampler.STRATA},
        "independent_NT_pseudo_gold_evaluation": blind,
        "semantic_gold_human_reviewed": 0,
        "unpaired_grammar_gold_reviewed": 0,
        "no_original_or_authored_text_changed": True,
        "original_macula_source_ids_preserved": True,
        "automatic_linguistic_approval": False,
        "publication_authorized": False,
    }
    return report, suggestions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "original-index", "correspondence-lock", "semantic-sample-lock",
        "pivot-lock", "pivot-nt", "pivot-ot", "curated-lock",
        "curated-root", "report", "private-agreements"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    if (args.report.resolve().is_relative_to(ROOT)
            or args.private_agreements.resolve().is_relative_to(ROOT)):
        raise ValueError("private hypotheses and reports must stay outside Git")
    if args.report.resolve() == args.private_agreements.resolve():
        raise ValueError("private candidate and source-free report paths collide")
    source_lock = json.loads(args.correspondence_lock.read_text(encoding="utf-8"))
    index, index_sha = phrase.pinned_index(args.original_index, source_lock)
    sample_lock = json.loads(args.semantic_sample_lock.read_text(encoding="utf-8"))
    raw, _ = sampler.render(index, source_lock, index_sha, per_stratum=500)
    if (hashlib.sha256(raw).hexdigest() != sample_lock[
            "private_unreviewed_cases_sha256"] or
            sample_lock["source_index_gzip_sha256"] != index_sha):
        raise ValueError("original sample and source index no longer frozen")
    samples = json.loads(raw)["cases"]
    pivot_lock = json.loads(args.pivot_lock.read_text(encoding="utf-8"))
    pivots = {}
    for canon, path in (("nt", args.pivot_nt), ("ot", args.pivot_ot)):
        pivots[canon], _ = lexical.pivot_source(
            path, canon, pivot_lock["sources"][canon]["sha256"])
    curated = json.loads(args.curated_lock.read_text(encoding="utf-8"))
    if curated["osis_sha256"] != source_lock["curated_osis_sha256"]:
        raise ValueError("curated authored LSG 1.0.2 identity changed")
    authored_file = bridge.ed.pinned_file(
        args.curated_root, curated["osis_path"], curated["osis_sha256"])
    authored = bridge.ed.read_osis(authored_file)
    report, suggestions = analyze(index, pivots, authored, samples)
    report.update({
        "original_index_gzip_sha256": index_sha,
        "source_clear_bible_revision": source_lock["source_clear_bible_revision"],
        "source_aquifer_revision": source_lock["source_aquifer_revision"],
        "curated_osis_sha256": curated["osis_sha256"],
        "frozen_sample_sha256": sample_lock["private_unreviewed_cases_sha256"],
        "pivot_revisions": {canon: pivot_lock["sources"][canon]["revision"]
                            for canon in ("nt", "ot")},
    })
    packed = phrase.compressed_private({
        "kind": "brsi-private-lexical-phrase-consensus-hypotheses",
        "source_index_gzip_sha256": index_sha,
        "source_clear_bible_revision": source_lock["source_clear_bible_revision"],
        "authored_french_osis_sha256": curated["osis_sha256"],
        "candidate_only": True,
        "publication_authorized": False,
        "suggestions": suggestions,
    })
    report["private_agreements_sha256"] = hashlib.sha256(packed).hexdigest()
    report["private_agreements_bytes"] = len(packed)
    args.private_agreements.write_bytes(packed)
    args.report.write_text(
        json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print("BRSI_MACULA_LSG_LEXICAL_PHRASE_CONSENSUS_COUNTS",
          json.dumps({"full": report["source_coverage"],
                      "blind": report["independent_NT_pseudo_gold_evaluation"][
                          "blind_selected_threshold_metrics"],
                      "control": report["independent_NT_pseudo_gold_evaluation"][
                          "predeclared_exploratory_comparisons"],
                      "private_sha256": report["private_agreements_sha256"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
