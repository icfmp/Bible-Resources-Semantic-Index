#!/usr/bin/env python3
"""Explore MACULA lowfat syntax constituents vs exact authored LSG word anchors.

NONPUBLISHING, NONLINGUISTIC: syntax creates source-side phrase/orthographic
review units, *not* Greek/Hebrew ↔ French translation equivalences. Actual
authored French and original syntax text stay in a deterministic PRIVATE gzip.
Only source-text-free counts and pinned private digest may enter Git.

The original lowfat XML comes from the same byte-pinned MACULA revisions
already used for the existing Greek/Hebrew lexical TSV pivots. Test both
Testaments, including distinct Hebrew morphemes of the same orthographic word.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_syntax_phrase_existing", ROOT / "scripts" /
    "audit_macula_lsg_phrase_brackets.py")
phrase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phrase)
bridge = phrase.bridge
sampler = phrase.sampler

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
SOURCE_REF = re.compile(r"^([A-Z0-9]+)\s+([0-9]+):([0-9]+)!([0-9]+)$")
MAX_CONSTITUENT_ORIGINAL_IDS = 24
MAX_ANCHORED_FRENCH_CUE_WORDS = 16
# First fixed, real-source Hebrew/Greek witness pilot, NOT a handpicked
# substitute for a random Bible-wide quality estimate.
PILOT_FILES = (
    ("ot", "WLC/lowfat/01-Gen-001-lowfat.xml"),
    ("ot", "WLC/lowfat/01-Gen-002-lowfat.xml"),
    ("ot", "WLC/lowfat/01-Gen-003-lowfat.xml"),
    ("nt", "SBLGNT/lowfat/24-2john.xml"),
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def source_verse(source: str) -> str:
    if (len(source) < 10 or source[0] not in "no" or not source[1:].isdecimal()):
        raise ValueError("malformed original MACULA token ID")
    return source[1:9]


def parse_original_syntax(
        xml_bytes: bytes, canon: str, file_name: str,
        *, max_group: int = MAX_CONSTITUENT_ORIGINAL_IDS) -> dict:
    """Keep document-order MACULA leaves and nested true XML <wg> groups.

    Source syntax is *not* reduced to text whitespace tokenization. The same
    @ref within a verse denotes the same **original orthographic word**,
    which may include multiple Hebrew morphemes with distinct XML IDs.
    """
    if canon not in ("nt", "ot") or max_group < 2:
        raise ValueError("unknown Testament or constituent bound")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("original MACULA lowfat XML is invalid") from exc
    if root.tag not in ("book", "chapter") or not root.get("id"):
        raise ValueError("unexpected original lowfat book/chapter root")
    book = root.get("id").split()[0]
    prefix = "n" if canon == "nt" else "o"
    tokens = {}
    by_verse = defaultdict(list)
    by_ref = defaultdict(list)
    missing_surface = 0
    for leaf in root.iter("w"):
        source = leaf.get(XML_ID)
        if not source or not source.startswith(prefix):
            raise ValueError("source XML ID absent or in wrong Testament")
        verse = source_verse(source)
        ref = leaf.get("ref") or ""
        m = SOURCE_REF.fullmatch(ref)
        if (not m or m.group(1) != book or
                int(m.group(2)) != int(verse[2:5]) or
                int(m.group(3)) != int(verse[5:8])):
            raise ValueError("source XML original word and reference disagreement")
        if source in tokens:
            raise ValueError("duplicate original XML token ID")
        surface = leaf.get("unicode") or leaf.text or leaf.get("normalized")
        missing_surface += int(not bool(surface))
        tokens[source] = {
            "source_id": source,
            "original_orthographic_word_ref": ref,
            "original_surface": surface,
            "original_lemma": leaf.get("lemma"),
            "original_morphology": leaf.get("morph"),
            "original_class": leaf.get("class"),
            "original_part_of_speech": leaf.get("pos"),
            "original_semantic_role": leaf.get("role"),
            "original_language": root.get("lang"),
        }
        by_verse[verse].append(source)
        by_ref[ref].append(source)
    if not tokens:
        raise ValueError("original MACULA lowfat contains no word data")
    position = {
        source: ordinal for verse, ids in by_verse.items()
        for ordinal, source in enumerate(ids)}
    constituents = []
    diagnostics = Counter()
    parents = {child: node for node in root.iter() for child in node}
    for serial, group in enumerate(root.iter("wg"), 1):
        ids = [w.get(XML_ID) for w in group.iter("w")]
        if len(ids) < 2:
            diagnostics["single_source_id_group"] += 1
            continue
        if len(ids) > max_group:
            diagnostics["too_large_group"] += 1
            continue
        verses = {source_verse(source) for source in ids}
        if len(verses) != 1:
            diagnostics["cross_verse_group_rejected"] += 1
            continue
        verse = next(iter(verses))
        ordered = [position[source] for source in ids]
        if ordered != list(range(ordered[0], ordered[0] + len(ordered))):
            raise ValueError("source syntax constituent is not contiguous in original XML")
        depth = 0
        current = group
        while current in parents:
            depth += 1
            current = parents[current]
        constituents.append({
            "source_verse": verse,
            "group_id": f"{file_name}:wg:{serial}",
            "original_macula_ids": ids,
            "original_group_class": group.get("class"),
            "original_group_rule": group.get("rule"),
            "original_group_role": group.get("role"),
            "original_group_predication": group.get("predication"),
            "original_source_syntax_depth": depth,
            "source_side_only_not_translated_phrase": True,
        })
        diagnostics["eligible_2_to_24_source_group"] += 1
    by_source = defaultdict(list)
    for group in constituents:
        for source in group["original_macula_ids"]:
            by_source[source].append(group)
    preferred = {}
    for source, groups in by_source.items():
        preferred[source] = min(
            groups, key=lambda g: (len(g["original_macula_ids"]),
                                   -g["original_source_syntax_depth"],
                                   g["group_id"]))
    return {
        "canon": canon, "book": book, "source_file": file_name,
        "source_xml_sha256": sha(xml_bytes),
        "tokens": tokens,
        "verses": dict(sorted(by_verse.items())),
        "orthographic_words": dict(sorted(by_ref.items())),
        "all_eligible_constituents": constituents,
        "preferred_by_source": preferred,
        "diagnostics": dict(sorted(diagnostics.items())),
        "source_tokens_without_original_surface": missing_surface,
    }


def review_cue(
        index: dict, authored: dict[str, str], group: dict,
        *, max_cue: int = MAX_ANCHORED_FRENCH_CUE_WORDS) -> dict:
    """Only locate **already-attested anchors**, never infer an unlinked word.

    The inclusive first-to-last anchor region is a review/navigation *cue*,
    NOT the French rendering of all original words in the constituent.
    """
    verse = group["source_verse"]
    original_ids = group["original_macula_ids"]
    if not verse in authored:
        return {"exact_authored_french_verse_exists": False,
                "source_anchor_count": 0, "french_anchor_word_ids": [],
                "french_cue_word_ids": [],
                "unreviewed_reordering_witness": False}
    french = bridge.word_tokens(authored[verse])
    anchors = []
    for original in original_ids:
        result = phrase.exact_anchor(index, original)
        if result is None:
            continue
        word, ordinal = result
        if not 1 <= ordinal <= len(french):
            raise ValueError("source alignment anchor exceeds exact authored LSG verse")
        if word != f"{verse}:{ordinal}":
            raise ValueError("source anchor does not match authorial French verse")
        anchors.append((original, word, ordinal))
    ordinals = [a[2] for a in anchors]
    different = sorted(set(ordinals))
    cue = []
    if len(different) >= 2 and different[-1] - different[0] + 1 <= max_cue:
        cue = [f"{verse}:{i}" for i in
               range(different[0], different[-1] + 1)]
    # Reversed order of *attested* sources/French anchors is not automatically
    # false: Greek and Hebrew frequently reorder French noun/verb phrases.
    return {
        "exact_authored_french_verse_exists": True,
        "source_anchor_count": len(anchors),
        "distinct_french_anchor_locations": len(different),
        "french_anchor_word_ids": [a[1] for a in anchors],
        "french_cue_word_ids": cue,
        "unreviewed_reordering_witness": ordinals != sorted(ordinals),
        "multiple_original_ids_share_french_anchor": len(ordinals) != len(different),
        "french_cue_is_not_original_phrase_translation": True,
    }


def synthesize(
        index: dict, authored: dict[str, str],
        parsed: list[dict], *,
        expected_pilot_files: tuple[tuple[str, str], ...] = PILOT_FILES
        ) -> tuple[dict, dict]:
    if {(x["canon"], x["source_file"]) for x in parsed} != set(
            expected_pilot_files) or len(parsed) != len(expected_pilot_files):
        raise ValueError("missing, duplicated or unexpected pinned syntax pilot source file")
    seen = set()
    selected_verses = set()
    source_tokens = {}
    orthographic = {}
    chosen = {}
    source_groups = Counter()
    parse_stats = Counter()
    for doc in parsed:
        ids = set(doc["tokens"])
        if seen.intersection(ids):
            raise ValueError("same original MACULA source ID across pilot books")
        seen.update(ids)
        selected_verses.update(doc["verses"])
        source_tokens.update(doc["tokens"])
        for ref, members in doc["orthographic_words"].items():
            if ref in orthographic:
                raise ValueError("repeated orthographic reference across book files")
            orthographic[ref] = members
        chosen.update(doc["preferred_by_source"])
        source_groups[doc["canon"]] += len(doc["all_eligible_constituents"])
        parse_stats.update(doc["diagnostics"])
    full = index["by_original_macula_id"]
    unresolved = index["unlinked_cause_by_original_macula_id"]
    if not set(unresolved).issubset(full):
        raise ValueError("unlinked original IDs not a subset of pinned index")
    selected_index = {src for src in full if source_verse(src) in selected_verses}
    missing_from_xml = selected_index - seen
    # A genuine original-XML TSV reconciliation issue must be reported,
    # never invented or fixed by assigning the nearest token.
    missing_from_index = seen - selected_index
    mapped_selected = selected_index & seen
    cases = []
    by_canon = defaultdict(Counter)
    by_cause = defaultdict(Counter)
    for original in sorted(mapped_selected):
        if original not in unresolved:
            continue
        canon = "nt" if original.startswith("n") else "ot"
        reason = unresolved[original]
        verse = source_verse(original)
        current = source_tokens[original]
        reference = current["original_orthographic_word_ref"]
        siblings = orthographic[reference]
        linked_sibling = [
            source for source in siblings if source != original
            and source in full and phrase.exact_anchor(index, source) is not None]
        same_group = chosen.get(original)
        cue = review_cue(index, authored, same_group) if same_group else None
        by_canon[canon]["unlinked_original_ids"] += 1
        by_cause[reason]["unlinked_original_ids"] += 1
        if len(siblings) > 1:
            by_canon[canon]["within_multi_morpheme_orthographic_word"] += 1
            by_cause[reason]["within_multi_morpheme_orthographic_word"] += 1
        if linked_sibling:
            by_canon[canon]["same_original_word_has_preexisting_french_anchor"] += 1
            by_cause[reason]["same_original_word_has_preexisting_french_anchor"] += 1
        if same_group:
            by_canon[canon]["in_small_macula_syntax_constituent"] += 1
            by_cause[reason]["in_small_macula_syntax_constituent"] += 1
            if cue["source_anchor_count"] >= 1:
                by_canon[canon]["syntax_constituent_with_existing_french_anchor"] += 1
                by_cause[reason]["syntax_constituent_with_existing_french_anchor"] += 1
            if cue["french_cue_word_ids"]:
                by_canon[canon]["syntax_constituent_with_bounded_anchor_review_cue"] += 1
                by_cause[reason]["syntax_constituent_with_bounded_anchor_review_cue"] += 1
        cases.append({
            "original_macula_id": original,
            "canon": canon, "original_verse": verse,
            "source_unlinked_cause": reason,
            "original_orthographic_word_ref": reference,
            "original_same_word_morpheme_ids": siblings,
            "existing_french_anchored_morpheme_siblings": linked_sibling,
            "original_lowfat_leaf": current,
            "minimum_source_syntactic_constituent": same_group,
            "existing_french_anchor_review_cue": cue,
            "authored_lsg_verse": authored.get(verse),
            "original_phrase_semantically_verified": False,
            "individual_source_token_translated": False,
            "source_grammar_explicitly_unpaired_assumed": False,
            "requires_independent_original_language_review": True,
            "automatic_word_links_added": 0,
            "publication_authorized": False,
        })
    exact_french_available = sum(verse in authored for verse in selected_verses)
    for doc in parsed:
        doc["source_file"] = str(doc["source_file"])
    private = {
        "kind": "brsi-private-macula-syntax-source-original-phrase-review-pilot",
        "schema_version": 1,
        "source_original_xml_files": [
            {"canon": d["canon"], "source_file": d["source_file"],
             "sha256": d["source_xml_sha256"]}
            for d in parsed],
        "cases": cases,
        "source_tokens_not_in_existing_index": sorted(missing_from_index),
        "indexed_source_tokens_missing_from_selected_lowfat":
            sorted(missing_from_xml),
        "source_originals_modified": False,
        "source_text_modified": False,
        "semantic_links_approved": 0,
        "publication_authorized": False,
    }
    report = {
        "kind": "brsi-original-macula-lowfat-syntax-source-phrase-review-only-pilot",
        "schema_version": 1,
        "pilot_scope": "Genesis_1_to_3_and_2_John_only_not_bible_wide",
        "source_files": private["source_original_xml_files"],
        "source_xml_total_original_token_ids": len(seen),
        "source_verse_count": len(selected_verses),
        "source_verses_with_exact_authored_LSG": exact_french_available,
        "original_source_XML_ids_already_in_correspondence_index": len(mapped_selected),
        "original_XML_context_only_ids_absent_correspondence_index":
            len(missing_from_index),
        "correspondence_index_source_ids_not_in_selected_XML":
            len(missing_from_xml),
        "eligible_original_lowfat_syntactic_group_count":
            dict(sorted(source_groups.items())),
        "lowfat_syntax_group_rejection_counters": dict(sorted(parse_stats.items())),
        "unresolved_original_ids_in_selected_source_documents": len(cases),
        "unresolved_original_by_testament": {
            c:dict(sorted(row.items())) for c,row in sorted(by_canon.items())},
        "unresolved_original_by_frozen_stratum": {
            c:dict(sorted(by_cause[c].items())) for c in sampler.STRATA},
        "new_individually_approved_MACULA_original_ids": 0,
        "new_semantically_approved_source_phrases": 0,
        "human_reviewed_original_phrases": 0,
        "original_orthographic_sibling_evidence_is_not_french_translation": True,
        "syntactic_constituent_is_not_semantic_equivalence": True,
        "french_anchor_cue_is_not_translation_of_original_phrase": True,
        "no_source_or_authored_lsg_text_modification": True,
        "publication_authorized": False,
        "source_text_in_public_receipt": False,
    }
    return private, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("original-index", "correspondence-lock", "pivot-lock",
                "original-nt-root", "original-ot-root",
                "curated-root", "curated-lock", "private-syntax",
                "report"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    for path in (args.private_syntax, args.report):
        if path.resolve().is_relative_to(ROOT):
            raise ValueError("original syntax private data must not be committed")
    if args.private_syntax.resolve() == args.report.resolve():
        raise ValueError("private original contexts and report output must differ")
    source_lock = json.loads(args.correspondence_lock.read_text(encoding="utf-8"))
    index, index_sha = phrase.pinned_index(args.original_index, source_lock)
    pivot = json.loads(args.pivot_lock.read_text(encoding="utf-8"))
    edition = json.loads(args.curated_lock.read_text(encoding="utf-8"))
    if edition["osis_sha256"] != source_lock["curated_osis_sha256"]:
        raise ValueError("curated French edition changed")
    osis = bridge.ed.pinned_file(
        args.curated_root, edition["osis_path"], edition["osis_sha256"])
    authored = bridge.ed.read_osis(osis)
    parsed = []
    for canon, filename in PILOT_FILES:
        path = ((args.original_nt_root if canon == "nt" else args.original_ot_root)
                / filename)
        parsed.append(parse_original_syntax(path.read_bytes(), canon, filename))
    private, receipt = synthesize(index, authored, parsed)
    packed = phrase.compressed_private(private)
    receipt.update({
        "source_index_gzip_sha256": index_sha,
        "original_clear_bible_revision": source_lock["source_clear_bible_revision"],
        "source_aquifer_revision": source_lock["source_aquifer_revision"],
        "original_macula_lowfat_revisions": {
            canon: pivot["sources"][canon]["revision"] for canon in ("nt", "ot")},
        "exact_authored_french_osis_sha256": edition["osis_sha256"],
        "private_syntax_gzip_sha256": sha(packed),
        "private_syntax_gzip_bytes": len(packed),
    })
    args.private_syntax.write_bytes(packed)
    args.report.write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) +
        "\n", encoding="utf-8")
    print("BRSI_MACULA_ORIGINAL_SYNTAX_SOURCE_FREE_COUNTS",
          json.dumps({
              "original_XML_tokens": receipt["source_xml_total_original_token_ids"],
              "source_verses": receipt["source_verse_count"],
              "unresolved": receipt["unresolved_original_ids_in_selected_source_documents"],
              "testament": receipt["unresolved_original_by_testament"],
              "private_SHA256": receipt["private_syntax_gzip_sha256"],
          }, sort_keys=True))


if __name__ == "__main__":
    main()
