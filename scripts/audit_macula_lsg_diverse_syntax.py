#!/usr/bin/env python3
"""Broad mixed-genre MACULA source-syntax review units against pinned LSG.

Extends the verified original-source lowfat parser without changing it or
disturbing the independently locked Genesis 1–3 / 2 John pilot. These are
*deliberately diverse book/chapter witnesses*, NOT a statistically random
Bible-wide sample, semantic Greek/Hebrew↔French aligned pairs, or gold.

Retain original source-phrase roles, morphological word siblings, canonical
source IDs and only existing French word anchors. The private source/text
payload stays outside Git; the pinned receipt is source-text-free.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_lowfat_multigenre_helper", ROOT / "scripts" /
    "audit_macula_lsg_original_syntax.py")
syntax = importlib.util.module_from_spec(spec)
spec.loader.exec_module(syntax)
phrase = syntax.phrase
bridge = syntax.bridge
sampler = syntax.sampler

# Literary labels describe the DESIGN of this test cohort only; they
# are not grammar/genre labels imported from or supplied by MACULA.
# Every entry is fetched from the exact revisions in pivot.lock.json.
BREADTH_SOURCES = (
    ("ot", "WLC/lowfat/02-Exo-020-lowfat.xml", "law_covenant"),
    ("ot", "WLC/lowfat/03-Lev-019-lowfat.xml", "law_covenant"),
    ("ot", "WLC/lowfat/05-Deu-006-lowfat.xml", "law_covenant"),
    ("ot", "WLC/lowfat/08-Rut-001-lowfat.xml", "narrative"),
    ("ot", "WLC/lowfat/09-1Sa-017-lowfat.xml", "narrative"),
    ("ot", "WLC/lowfat/18-Job-001-lowfat.xml", "wisdom"),
    ("ot", "WLC/lowfat/19-Psa-023-lowfat.xml", "poetry"),
    ("ot", "WLC/lowfat/20-Pro-003-lowfat.xml", "wisdom"),
    ("ot", "WLC/lowfat/21-Ecc-001-lowfat.xml", "wisdom"),
    ("ot", "WLC/lowfat/23-Isa-053-lowfat.xml", "prophecy"),
    ("ot", "WLC/lowfat/27-Dan-007-lowfat.xml", "apocalyptic"),
    ("ot", "WLC/lowfat/32-Jon-001-lowfat.xml", "narrative"),
    ("ot", "WLC/lowfat/38-Zec-004-lowfat.xml", "prophecy"),
    ("nt", "SBLGNT/lowfat/02-mark.xml", "gospel_narrative"),
    ("nt", "SBLGNT/lowfat/06-romans.xml", "theological_argument"),
    ("nt", "SBLGNT/lowfat/18-philemon.xml", "letter"),
    ("nt", "SBLGNT/lowfat/20-james.xml", "practical_exhortation"),
    ("nt", "SBLGNT/lowfat/27-revelation.xml", "apocalyptic"),
)
BREADTH_FILES = tuple((canon, path) for canon, path, _ in BREADTH_SOURCES)


def review_units(cases: list[dict]) -> tuple[list[dict], dict]:
    """Deduplicate source-syntax review clusters—never split into links."""
    clusters: dict[str, dict] = {}
    by_grammar = collections.Counter()
    cases_without_syntax = 0
    for c in cases:
        source = c["original_macula_id"]
        syntax_group = c["minimum_source_syntactic_constituent"]
        if syntax_group is None:
            cases_without_syntax += 1
            continue
        group_id = syntax_group["group_id"]
        cue = c["existing_french_anchor_review_cue"]
        if not cue:
            raise ValueError("original constituent has no authored cue object")
        if group_id not in clusters:
            clusters[group_id] = {
                "review_group_id": group_id,
                "original_source_verse": syntax_group["source_verse"],
                "original_macula_ids": syntax_group["original_macula_ids"],
                "original_syntax_class": syntax_group["original_group_class"],
                "original_syntax_rule": syntax_group["original_group_rule"],
                "original_syntax_role": syntax_group["original_group_role"],
                "original_syntax_depth": syntax_group["original_source_syntax_depth"],
                "unlinked_original_macula_ids": [],
                "unlinked_source_cause_counts": {},
                "exact_authored_french_anchor_word_ids":
                    cue["french_anchor_word_ids"],
                "authored_french_review_cue_word_ids":
                    cue["french_cue_word_ids"],
                "word_reordering_from_existing_anchors_not_semantically_adjudicated":
                    cue["unreviewed_reordering_witness"],
                "many_original_to_one_french_anchor_witness":
                    cue["multiple_original_ids_share_french_anchor"],
                "source_syntax_unit_only": True,
                "whole_original_phrase_translated_to_french_not_proven": True,
                "new_source_french_links_approved": 0,
                "publication_authorized": False,
            }
        cluster = clusters[group_id]
        if (cluster["original_source_verse"] != c["original_verse"] or
                source not in cluster["original_macula_ids"] or
                cluster["exact_authored_french_anchor_word_ids"] !=
                cue["french_anchor_word_ids"]):
            raise ValueError("incompatible original-source or French anchor review group")
        cluster["unlinked_original_macula_ids"].append(source)
        reason = c["source_unlinked_cause"]
        counter = cluster["unlinked_source_cause_counts"]
        counter[reason] = counter.get(reason, 0) + 1
        gram_class = syntax_group["original_group_class"] or "unspecified"
        by_grammar[gram_class] += 1

    groups = []
    by_type = collections.Counter()
    for group_id, unit in sorted(clusters.items()):
        sources = unit["unlinked_original_macula_ids"]
        unit["unlinked_original_macula_ids"] = sorted(sources)
        unit["unlinked_source_cause_counts"] = dict(
            sorted(unit["unlinked_source_cause_counts"].items()))
        verse = unit["original_source_verse"]
        if not all(syntax.source_verse(x) == verse for x in unit["original_macula_ids"]):
            raise ValueError("cross-verse original review unit")
        if any(not word_id.startswith(verse+":")
               for word_id in unit["authored_french_review_cue_word_ids"]):
            raise ValueError("cross-verse original↔French navigation cue")
        if len(set(sources)) != len(sources):
            raise ValueError("repeated source token in one review unit")
        group_sources = unit["original_macula_ids"]
        if len(group_sources) > syntax.MAX_CONSTITUENT_ORIGINAL_IDS:
            raise ValueError("oversize grouped source phrase")
        by_type["original_constituent_review_units"] += 1
        by_type["original_ids_represented_in_review_units"] += len(sources)
        if unit["authored_french_review_cue_word_ids"]:
            by_type["source_review_units_with_bounded_french_navigation_cue"] += 1
        if unit["exact_authored_french_anchor_word_ids"]:
            by_type["source_review_units_with_at_least_one_existing_french_anchor"] += 1
        if unit["word_reordering_from_existing_anchors_not_semantically_adjudicated"]:
            by_type["reordered_existing_french_anchor_review_units"] += 1
        if unit["many_original_to_one_french_anchor_witness"]:
            by_type["shared_existing_french_anchor_review_units"] += 1
        groups.append(unit)
    by_type["unlinked_original_ids_without_bounded_syntax_unit"] = cases_without_syntax
    return groups, {
        **dict(sorted(by_type.items())),
        "distinct_original_syntactic_class_counts_for_unlinked_original_ids":
            dict(sorted(by_grammar.items())),
    }


def per_source_file(parsed: list[dict], cases: list[dict], index: dict) -> list[dict]:
    """Book-specific counts make genre and OT-vs-NT asymmetry inspectable."""
    case_by_verse = collections.defaultdict(list)
    for c in cases:
        case_by_verse[c["original_verse"]].append(c)
    res = []
    indexed_sources = index["by_original_macula_id"]
    genre_map = {(canon, name): genre
                 for canon, name, genre in BREADTH_SOURCES}
    for doc in parsed:
        canon, name = doc["canon"], doc["source_file"]
        in_scope = [c for verse in doc["verses"]
                    for c in case_by_verse[verse]]
        if any(c["canon"] != canon for c in in_scope):
            raise ValueError("source verse reused in wrong Testament")
        counted = collections.Counter()
        original_ids = set(doc["tokens"])
        source_only_ids = original_ids.difference(indexed_sources)
        counted["source_XML_ids_absent_original_correspondence_index"] = len(
            source_only_ids)
        counted["source_XML_ids_with_nonnumeric_original_selector"] = sum(
            not source[1:].isascii() or not source[1:].isdecimal()
            for source in original_ids)
        counted["source_only_IDs_with_nonnumeric_original_selector"] = sum(
            not source[1:].isascii() or not source[1:].isdecimal()
            for source in source_only_ids)
        counted["source_only_IDs_with_decimal_original_selector"] = (
            len(source_only_ids)
            - counted["source_only_IDs_with_nonnumeric_original_selector"])
        for case in in_scope:
            counted["unlinked_indexed_original_ids"] += 1
            if case["minimum_source_syntactic_constituent"]:
                counted["inside_real_bounded_original_syntax"] += 1
            cue = case["existing_french_anchor_review_cue"]
            if cue:
                if cue["source_anchor_count"] >= 1:
                    counted["original_syntax_group_with_existing_french_anchor"] += 1
                if cue["french_cue_word_ids"]:
                    counted["original_syntax_group_with_french_navigation_cue"] += 1
                if cue["unreviewed_reordering_witness"]:
                    counted["original_group_has_reordered_existing_anchor_evidence"] += 1
            if case["existing_french_anchored_morpheme_siblings"]:
                counted["original_word_sibling_already_has_french_anchor"] += 1
            if len(case["original_same_word_morpheme_ids"]) > 1:
                counted["inside_multi_morpheme_orthographic_word"] += 1
        res.append({
            "canon": canon, "source_file": name,
            "study_genre_cohort_label_not_macula_metadata":
                genre_map[(canon, name)],
            "source_verse_count": len(doc["verses"]),
            "original_macula_source_xml_id_count": len(doc["tokens"]),
            "small_source_constituents": len(doc["all_eligible_constituents"]),
            "source_xml_sha256": doc["source_xml_sha256"],
            **dict(sorted(counted.items())),
        })
    return res


def breadth(
        index: dict, authored: dict[str, str], parsed: list[dict]
        ) -> tuple[dict, dict]:
    expected = {(c, n) for c, n, _ in BREADTH_SOURCES}
    if len(expected) != len(BREADTH_SOURCES):
        raise ValueError("duplicate selected original source filename")
    private, base = syntax.synthesize(
        index, authored, parsed, expected_pilot_files=BREADTH_FILES)
    grouped, grammar = review_units(private["cases"])
    byfile = per_source_file(parsed, private["cases"], index)
    if len(byfile) != len(BREADTH_SOURCES):
        raise ValueError("missing selected original-language source witness")
    if (sum(x["source_XML_ids_absent_original_correspondence_index"]
            for x in byfile) !=
            base["original_XML_context_only_ids_absent_correspondence_index"]):
        raise ValueError("per-source-book original XML↔index reconciliation mismatch")
    # Source-only numeric IDs and authentic suffixed IDs are distinct
    # anomalies to investigate: neither authorizes an index repair.
    selector_totals = {
        "source_XML_context_only_nonnumeric_selector_ids": sum(
            x["source_only_IDs_with_nonnumeric_original_selector"]
            for x in byfile),
        "source_XML_context_only_decimal_selector_ids": sum(
            x["source_only_IDs_with_decimal_original_selector"]
            for x in byfile),
        "all_source_XML_nonnumeric_selector_ids": sum(
            x["source_XML_ids_with_nonnumeric_original_selector"]
            for x in byfile),
    }
    if (selector_totals["source_XML_context_only_nonnumeric_selector_ids"] +
            selector_totals["source_XML_context_only_decimal_selector_ids"] !=
            base["original_XML_context_only_ids_absent_correspondence_index"]):
        raise ValueError("source-only ID selector class accounting differs from pinned index")
    if sum(x["unlinked_indexed_original_ids"] for x in byfile) != len(private["cases"]):
        raise ValueError("per-source-file unresolved audit incomplete")
    if (grammar["original_ids_represented_in_review_units"] +
            grammar["unlinked_original_ids_without_bounded_syntax_unit"] !=
            len(private["cases"])):
        raise ValueError("unresolved original source review unit accounting incomplete")
    if (sum(x["original_macula_source_xml_id_count"] for x in byfile) !=
            base["source_xml_total_original_token_ids"]):
        raise ValueError("original source manuscript word counts disagree")
    if (sum(x["source_verse_count"] for x in byfile) !=
            base["source_verse_count"]):
        raise ValueError("verse-level original manuscript witness overlap")
    private["kind"] = "brsi-private-diverse-original-macula-syntax-review-units"
    private["source_side_syntax_review_units"] = grouped
    private["source_text_preserved_no_translation_equivalence_generated"] = True
    base["kind"] = "brsi-diverse-original-syntax-review-units-nonpublishing"
    base["schema_version"] = 1
    base["pilot_scope"] = (
        "fixed_13_OT_chapter_and_5_NT_complete_books_diverse_nonrandom_sources")
    base["study_selection_is_random_or_representative"] = False
    base["study_genres_are_design_metadata_not_source_labels"] = True
    base["authored_LSG_french_phrases_must_be_human_verified"] = True
    base["source_side_review_units"] = {
        "total": len(grouped), **grammar,
    }
    base["per_source_document"] = byfile
    base["original_source_selector_reconciliation"] = selector_totals
    base["human_gold_original_to_authored_french_phrase_cases"] = 0
    base["new_french_word_or_phrase_links_approved"] = 0
    base["translation_accuracy_measured"] = False
    base["publication_authorized"] = False
    return private, base


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for field in (
        "original-index", "correspondence-lock", "pivot-lock",
        "original-nt-root", "original-ot-root", "curated-root",
        "curated-lock", "private-dossiers", "report"):
        p.add_argument("--" + field, required=True, type=Path)
    args = p.parse_args()
    if (args.private_dossiers.resolve().is_relative_to(ROOT) or
            args.report.resolve().is_relative_to(ROOT) or
            args.private_dossiers.resolve() == args.report.resolve()):
        raise ValueError("private source syntax and audit report must remain outside repo")
    correspondence = json.loads(
        args.correspondence_lock.read_text(encoding="utf-8"))
    index, sha = phrase.pinned_index(args.original_index, correspondence)
    pivot = json.loads(args.pivot_lock.read_text(encoding="utf-8"))
    curated = json.loads(args.curated_lock.read_text(encoding="utf-8"))
    if curated["osis_sha256"] != correspondence["curated_osis_sha256"]:
        raise ValueError("authored French edition changed")
    french_file = bridge.ed.pinned_file(
        args.curated_root, curated["osis_path"], curated["osis_sha256"])
    authored = bridge.ed.read_osis(french_file)
    parsed = []
    for canon, name, _genre in BREADTH_SOURCES:
        path = ((args.original_nt_root if canon == "nt"
                 else args.original_ot_root) / name)
        parsed.append(syntax.parse_original_syntax(
            path.read_bytes(), canon, name))
    private, report = breadth(index, authored, parsed)
    packed = phrase.compressed_private(private)
    report.update({
        "source_index_gzip_sha256": sha,
        "original_clear_bible_revision":
            correspondence["source_clear_bible_revision"],
        "source_aquifer_revision":
            correspondence["source_aquifer_revision"],
        "original_macula_lowfat_revisions": {
            canon: pivot["sources"][canon]["revision"]
            for canon in ("nt", "ot")},
        "exact_authored_french_osis_sha256": curated["osis_sha256"],
        "private_dossiers_gzip_sha256":
            hashlib.sha256(packed).hexdigest(),
        "private_dossiers_gzip_bytes": len(packed),
    })
    args.private_dossiers.write_bytes(packed)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n", encoding="utf-8")
    print("BRSI_MACULA_DIVERSE_SYNTAX_SOURCE_FREE_COUNTS",
          json.dumps({
              "original_xml_ids": report["source_xml_total_original_token_ids"],
              "index_original_ids":
                  report["original_source_XML_ids_already_in_correspondence_index"],
              "source_verses": report["source_verse_count"],
              "unlinked_original_ids":
                  report["unresolved_original_ids_in_selected_source_documents"],
              "review_units": report["source_side_review_units"]["total"],
              "reordering_units":
                  report["source_side_review_units"].get(
                      "reordered_existing_french_anchor_review_units", 0),
              "private_sha256": report["private_dossiers_gzip_sha256"],
          }, sort_keys=True))


if __name__ == "__main__":
    main()
