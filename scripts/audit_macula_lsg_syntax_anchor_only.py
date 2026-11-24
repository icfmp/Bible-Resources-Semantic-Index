#!/usr/bin/env python3
"""Measure authentic MACULA syntax-group French brackets WITHOUT a lemma filter.

This read-only follow-up to the syntax/lexical negative control deliberately
separates (a) existing source-attested French anchors, (b) a *navigation*
interval spanning those anchors, and (c) an independently reviewed bilingual
translation phrase (which this script DOES NOT establish).

The 600 previously defined NT retrospective pseudo-gold verses are held out
by original verse, and all sources sharing the tested French target are masked.
No new word or phrase correspondence is approved or distributed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "brsi_existing_source_syntax_lexical_control",
    ROOT / "scripts" / "audit_macula_lsg_syntax_lexical_neighborhood.py")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
syntax = base.syntax
phrase = base.phrase
bridge = base.bridge
lexical = base.lexical
sampler = base.sampler
diverse = base.diverse

WIDTH_LIMITS = (4, 8, 12, 16)
MIN_CAL_ATTEMPTS = 25
MIN_CAL_CONTAINMENT = .9
MIN_CAL_WILSON95 = .75


def anchor_bracket(
    index: dict, authored: dict[str, str], original: str,
    groups: list[dict], *, max_width: int = 16,
    hidden_source: str | None = None,
    hidden_word: str | None = None,
    french_cache: dict | None = None,
) -> dict | None:
    """Select a real source constituent, never an ordinal invented source run.

    At least TWO DIFFERENT independently already-located authored French
    words must be anchored inside the very same original XML constituent.
    Such a window is NOT certified to translate its source constituents.
    """
    if max_width < 2 or not groups:
        return None
    verse = syntax.source_verse(original)
    if verse not in authored:
        return None
    if french_cache is None:
        french_cache = {}
    words = lexical.words_in_verse(verse, authored, french_cache)
    options = []
    for group in groups:
        if group["source_verse"] != verse or original not in group["original_macula_ids"]:
            raise ValueError("source ID not in original XML constituent and verse")
        anchors = base.original_group_anchors(
            index, group["original_macula_ids"], len(words),
            hidden_source=hidden_source, hidden_word=hidden_word)
        positions = sorted({position for _source, _word, position in anchors})
        if len(positions) < 2:
            continue
        first, last = positions[0], positions[-1]
        if last - first + 1 > max_width:
            continue
        if hidden_word and hidden_word in (word for _source, word, _p in anchors):
            raise ValueError("held-out French target leaked into existing anchors")
        proposal = {
            "original_macula_id_under_review": original,
            "original_source_verse": verse,
            "authentic_MACULA_source_group_id": group["group_id"],
            "original_macula_phrase_ids": group["original_macula_ids"],
            "original_syntax_class": group["original_group_class"],
            "original_syntax_role": group["original_group_role"],
            "original_syntax_rule": group["original_group_rule"],
            "existing_source_french_anchors": [
                {"original_macula_id": source, "lsg_word_id": word}
                for source, word, _position in anchors],
            "bounded_authored_french_navigation_word_ids": [
                f"{verse}:{p}" for p in range(first, last + 1)],
            "span_width": last - first + 1,
            "independently_located_distinct_anchor_words": len(positions),
            # Original source coordinates are independently reproduced, but
            # this does NOT make the contextual translation semantics gold.
            "existing_anchor_evidence_tier": (
                "clear_bible_direct_nt_word_location_not_semantic_gold"
                if original.startswith("n") else
                "aquifer_surface_attested_ot_candidate_not_semantic_gold"),
            "lexical_translation_guess_required": False,
            "source_group_is_authentic": True,
            "French_span_is_only_navigation_not_translation": True,
            "human_phrase_semantic_gold": False,
            "automatic_link_approvals": 0,
            "publication_authorized": False,
        }
        options.append((
            len(group["original_macula_ids"]), last - first + 1,
            -len(positions), group["group_id"], proposal))
    if not options:
        return None
    return min(options, key=lambda option: option[:4])[4]


def bracket_metric(known: dict[str, str], predictions: dict, width: int) -> dict:
    if set(known) != set(predictions):
        raise ValueError("evaluation source ID partition mismatch")
    attempted = contained = total_words = 0
    by_source_group_size = collections.Counter()
    for source, actual in known.items():
        proposal = predictions[source]
        if proposal is None or proposal["span_width"] > width:
            continue
        attempted += 1
        contained += int(actual in proposal["bounded_authored_french_navigation_word_ids"])
        total_words += proposal["span_width"]
        by_source_group_size[len(proposal["original_macula_phrase_ids"])] += 1
    p = contained / attempted if attempted else 0.
    z = 1.96
    if attempted:
        d = 1 + z * z / attempted
        lower = (p + z*z/(2*attempted) -
                 z * math.sqrt(p*(1-p)/attempted + z*z/(4*attempted**2))) / d
    else:
        lower = 0.
    return {
        "cases": len(known), "attempted": attempted,
        "contained_source_attested_pseudo_gold_word": contained,
        "missed_source_attested_pseudo_gold_word": attempted - contained,
        "abstained": len(known) - attempted,
        "positional_containment_not_phrase_semantic_precision": round(p, 5),
        "wilson95_lower": round(lower, 5),
        "average_french_navigation_width": round(total_words / attempted, 4)
        if attempted else 0,
        "original_group_size_distribution": dict(sorted(by_source_group_size.items())),
    }


def per_document_counts(scope: set[str], grouped: set[str],
                        candidates: list[dict], parsed: list[dict]) -> list[dict]:
    """Account for review yield by original source document, without text."""
    if not grouped.issubset(scope):
        raise ValueError("syntax groups not contained in original unlinked scope")
    by_id = {x["original_macula_id_under_review"]: x for x in candidates}
    if len(by_id) != len(candidates) or not set(by_id).issubset(grouped):
        raise ValueError("duplicate or out-of-scope anchor-only candidate")
    seen_source_ids = set()
    reports = []
    for doc in parsed:
        original_ids = set(doc["tokens"])
        if not seen_source_ids.isdisjoint(original_ids):
            raise ValueError("original MACULA ID repeated in different source documents")
        seen_source_ids.update(original_ids)
        source = scope.intersection(original_ids)
        active = grouped.intersection(original_ids)
        proposals = [by_id[x] for x in sorted(source.intersection(by_id))]
        reports.append({
            "original_XML_file": doc["source_file"],
            "canon": doc["canon"],
            "original_verses": len(doc["verses"]),
            "unlinked_original_IDs_in_scope": len(source),
            "unlinked_original_IDs_with_source_syntax": len(active),
            "unlinked_original_IDs_with_anchor_only_candidate": len(proposals),
            "distinct_real_source_constituents_with_candidates":
                len({p["authentic_MACULA_source_group_id"] for p in proposals}),
        })
    if not scope.issubset(seen_source_ids):
        raise ValueError("original unlinked review scope absent from original XML")
    if sum(x["unlinked_original_IDs_with_anchor_only_candidate"]
           for x in reports) != len(candidates):
        raise ValueError("per-book candidate counts differ from original IDs")
    return reports


def study(index: dict, pivots: dict, authored: dict[str, str],
          parsed: list[dict]) -> tuple[dict, dict]:
    groups, documents = base.syntax_families(parsed)
    actual_gold = base.select_nt_pseudo_gold(index, pivots, authored, documents)
    verses = {syntax.source_verse(original) for original in actual_gold}
    if len(actual_gold) != 600 or len(verses) != 600:
        raise ValueError("previous 600-distinct-NT-source-verse cohort changed")

    cache = {}
    pseudo = {
        source: anchor_bracket(
            index, authored, source, groups.get(source, []),
            hidden_source=source, hidden_word=actual, french_cache=cache)
        for source, actual in actual_gold.items()
    }
    for original, actual in actual_gold.items():
        if pseudo[original] is not None:
            if any(anchor["lsg_word_id"] == actual
                   for anchor in pseudo[original]["existing_source_french_anchors"]):
                raise ValueError("hidden gold anchor leak")

    ordered = sorted(actual_gold, key=lexical.stable_key)
    first = {s: actual_gold[s] for s in ordered[:300]}
    second = {s: actual_gold[s] for s in ordered[300:]}
    grid = [
        {"max_french_words": width,
         **bracket_metric(first, {s: pseudo[s] for s in first}, width)}
        for width in WIDTH_LIMITS
    ]
    qualifying = [
        row for row in grid
        if row["attempted"] >= MIN_CAL_ATTEMPTS
        and row["positional_containment_not_phrase_semantic_precision"] >= MIN_CAL_CONTAINMENT
        and row["wilson95_lower"] >= MIN_CAL_WILSON95
    ]
    chosen = (min(qualifying, key=lambda x: (
        -x["attempted"], x["max_french_words"]))["max_french_words"]
        if qualifying else None)
    reporting = {
        str(width): bracket_metric(
            second, {s: pseudo[s] for s in second}, width)
        for width in WIDTH_LIMITS
    }
    selected = (reporting[str(chosen)] if chosen is not None else
                bracket_metric(second, {s: None for s in second}, WIDTH_LIMITS[0]))

    unresolved = index["unlinked_cause_by_original_macula_id"]
    counts = collections.defaultdict(collections.Counter)
    proposals = []
    seen = set()
    for original in sorted(groups):
        if original not in unresolved:
            continue
        verse = syntax.source_verse(original)
        canon = documents[verse]["canon"]
        cause = unresolved[original]
        seen.add(original)
        counts[(canon, cause)]["has_eligible_source_syntax_group"] += 1
        proposal = anchor_bracket(
            index, authored, original, groups[original], french_cache=cache)
        if proposal is None:
            counts[(canon, cause)]["no_bounded_two_distinct_anchor_bracket"] += 1
            continue
        if proposal["automatic_link_approvals"] != 0:
            raise ValueError("research proposal improperly approved a link")
        counts[(canon, cause)]["anchor_only_source_syntax_review_proposals"] += 1
        counts[(canon, cause)]["total_bounded_french_words"] += proposal["span_width"]
        proposal["unlinked_source_cause"] = cause
        proposal["canon"] = canon
        # Private output only. The report intentionally contains neither
        # French text nor original original-language source text.
        proposal["authored_french_verse_private"] = authored[verse]
        proposal["source_original_form_private"] = documents[verse]["tokens"][
            original]["original_surface"]
        proposals.append(proposal)
    total_scope = {s for s in unresolved if
                   syntax.source_verse(s) in documents and
                   s in documents[syntax.source_verse(s)]["tokens"]}
    if not seen.issubset(total_scope):
        raise ValueError("source groups exceed original indexed unresolved scope")
    if len({p["original_macula_id_under_review"] for p in proposals}) != len(proposals):
        raise ValueError("duplicate proposed source ID")
    strata = {}
    for canon in ("nt", "ot"):
        strata[canon] = {}
        for cause in sampler.STRATA:
            n = sum(1 for s in total_scope if
                    documents[syntax.source_verse(s)]["canon"] == canon
                    and unresolved[s] == cause)
            strata[canon][cause] = {
                "total_original_unlinked_in_pinned_XML_scope": n,
                **dict(sorted(counts[(canon, cause)].items())),
            }
    private = {
        "kind": "brsi-private-authentic-syntax-French-anchor-only-review-brackets",
        "original_source_candidates": proposals,
        "retrospective_masked_NT_source_targets": actual_gold,
        "human_semantic_gold": 0,
        "automatic_approved_links": 0,
        "publication_authorized": False,
    }
    report = {
        "kind": "brsi-macula-authentic-syntax-anchor-only-bracket-research",
        "schema_version": 1,
        "source_scope": "same_18_pinned_MACULA_XML_witnesses_as_prior_pilot",
        "original_source_XML_files": len(parsed),
        "source_verses": len(documents),
        "original_MACULA_IDs": len(index["by_original_macula_id"]),
        "original_MACULA_unlinked_IDs": len(unresolved),
        "original_unlinked_in_selected_XML_scope": len(total_scope),
        "original_unlinked_with_source_syntax_group": len(seen),
        "original_unlinked_with_anchor_only_bracket": len(proposals),
        "distinct_original_XML_source_constituents_with_candidates":
            len({p["authentic_MACULA_source_group_id"] for p in proposals}),
        "per_original_source_document":
            per_document_counts(total_scope, seen, proposals, parsed),
        "by_original_unlinked_cause": strata,
        "previous_lexical_pilot_research_proposals": 55,
        "lexical_prematch_required": False,
        "human_reviewed_bilingual_phrase_gold": 0,
        "new_links_automatically_approved": 0,
        "publication_authorized": False,
        "original_macula_or_LSG_modified": False,
        "source_text_or_french_scripture_in_report": False,
        "retrospective_NT_evaluation": {
            "pseudo_gold_cases": len(actual_gold),
            "distinct_heldout_NT_source_verses": len(verses),
            "each_heldout_source_and_its_exact_french_target_anchors_masked": True,
            "no_lemma_training_or_lexical_guesses": True,
            "not_independently_human_checked_phrase_gold": True,
            "calibration": grid,
            "selected_width_from_calibration_only": chosen,
            "reporting_at_selected_width": selected,
            "separate_exploratory_reporting": reporting,
        },
    }
    return private, report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for item in (
        "original-index", "correspondence-lock", "pivot-lock", "pivot-nt",
        "pivot-ot", "curated-lock", "curated-root",
        "original-nt-root", "original-ot-root", "private-candidates", "report",
    ):
        p.add_argument("--" + item, type=Path, required=True)
    a = p.parse_args()
    if a.private_candidates.resolve().is_relative_to(ROOT) or \
            a.report.resolve().is_relative_to(ROOT) or \
            a.private_candidates.resolve() == a.report.resolve():
        raise ValueError("private source and French review output must remain outside repo")
    source_lock = json.loads(a.correspondence_lock.read_text(encoding="utf-8"))
    index, index_sha = phrase.pinned_index(a.original_index, source_lock)
    curated = json.loads(a.curated_lock.read_text(encoding="utf-8"))
    if curated["osis_sha256"] != source_lock["curated_osis_sha256"]:
        raise ValueError("wrong authored French edition")
    pivot_lock = json.loads(a.pivot_lock.read_text(encoding="utf-8"))
    pivots = {}
    for canon, file in (("nt", a.pivot_nt), ("ot", a.pivot_ot)):
        pivots[canon], _ = lexical.pivot_source(
            file, canon, pivot_lock["sources"][canon]["sha256"])
    authored = bridge.ed.read_osis(bridge.ed.pinned_file(
        a.curated_root, curated["osis_path"], curated["osis_sha256"]))
    parsed = [
        syntax.parse_original_syntax(
            ((a.original_nt_root if canon == "nt" else a.original_ot_root)
             / path).read_bytes(), canon, path)
        for canon, path, _genre in diverse.BREADTH_SOURCES
    ]
    private, report = study(index, pivots, authored, parsed)
    packed = phrase.compressed_private(private)
    report.update({
        "source_index_gzip_sha256": index_sha,
        "exact_authored_french_OSIS_sha256": curated["osis_sha256"],
        "source_clear_bible_revision": source_lock["source_clear_bible_revision"],
        "source_aquifer_revision": source_lock["source_aquifer_revision"],
        "macula_original_source_revisions": {
            canon: pivot_lock["sources"][canon]["revision"]
            for canon in ("nt", "ot")},
        "source_lowfat_XML_sha256": {
            doc["source_file"]: doc["source_xml_sha256"] for doc in parsed},
        "private_candidates_gzip_bytes": len(packed),
        "private_candidates_gzip_sha256": hashlib.sha256(packed).hexdigest(),
    })
    a.private_candidates.write_bytes(packed)
    a.report.write_text(json.dumps(report, ensure_ascii=False,
                                   sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print("MACULA_LSG_SOURCE_SYNTAX_ANCHOR_ONLY_RESEARCH_REPORT")
    print(a.report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
