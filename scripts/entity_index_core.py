#!/usr/bin/env python3
"""Shared deterministic BRSI entity identity and source-link finalization.

Used by the canonical native entity builder and by the historical migration
reproduction tests. Does not fetch ACAI, amend source records, or publish.
"""
from __future__ import annotations

from collections import defaultdict

CATEGORIES = {
    "people": "person",
    "places": "place",
    "groups": "group",
    "deities": "deity",
    "fauna": "fauna",
    "flora": "flora",
    "realia": "realia",
    "keyterms": "keyterm",
}
LINK_FIELDS = ("explicit_instances", "pronominal_referents", "subject_referents")

def canonical_source_corpus(source_lock: dict, raw_corpus: str) -> str:
    """Resolve an observed ACAI field label to a pinned source corpus key."""
    mapping = source_lock.get("source_corpora")
    if not isinstance(mapping, dict):
        raise ValueError("Missing pinned source corpus-name crosswalk")
    resolved = mapping.get(raw_corpus)
    if not isinstance(resolved, str) or resolved not in source_lock["source_editions"]:
        raise ValueError(f"Unrecognized original source corpus: {raw_corpus!r}")
    return resolved

def finalize_index(entries: list, quarantined: list, source_lock: dict,
                   source_absences: dict | None,
                   source_verse_absences: dict | None,
                   reference_qualifications: dict | None,
                   source_snapshot_sha256: str, source_record_count: int) -> dict:
    """Shared deterministic link/index validation for old and current BSI records."""
    entries.sort(key=lambda x: x["id"])
    assigned_ids = [entry["id"] for entry in entries]
    if len(set(assigned_ids)) != len(entries):
        raise ValueError("Two source records resolve to the same output entity ID")
    # Deliberately never select a single entity when two source records
    # mention the same original word. Preserve ambiguity and link type.
    candidates = defaultdict(set)
    for entry in entries:
        for field, corpora in entry["occurrences"].items():
            for corpus, groups in corpora.items():
                for group in groups:
                    for word in group:
                        standard_corpus = canonical_source_corpus(source_lock, corpus)
                        source_format = source_lock["source_editions"][standard_corpus]
                        expected_prefix = source_format["word_id_prefix"]
                        digits = source_format["word_id_digits"]
                        if (not isinstance(digits, int) or isinstance(digits, bool)
                                or digits < 8):
                            raise ValueError(
                                f"Invalid original word ID digit count for {standard_corpus}")
                        if not isinstance(word, str) or not word.startswith(expected_prefix):
                            raise ValueError(
                                f"{entry['id']}: {corpus} word prefix incompatible: {word!r}")
                        if (len(word) != digits + len(expected_prefix)
                                or not word[len(expected_prefix):].isascii()
                                or not word[len(expected_prefix):].isdigit()):
                            raise ValueError(
                                f"{entry['id']}: {corpus} malformed original word ID: {word!r}")
                        candidates[f"{standard_corpus}:{word}"].add((entry["id"], field))
    # A pinned-source audit may prove that an imported annotation refers to
    # a word ID that does not exist in the claimed original-language edition.
    # Keep all source groups in 'entities'; suppress only unsafe lookup claims
    # and emit a reversible, provenance-rich diagnostics record.
    if source_absences is None:
        source_absences = {
            "schema_version": 1, "corpus": "wlc",
            "source_edition": source_lock["source_editions"]["wlc"]["edition"],
            "word_ids": [], "provenance": [],
        }
    if type(source_absences.get("schema_version")) is not int or source_absences["schema_version"] != 1:
        raise ValueError("Unsupported missing-word audit schema")
    corpus = source_absences.get("corpus")
    edition = source_absences.get("source_edition")
    catalog = source_lock["source_editions"].get(corpus)
    if not isinstance(catalog, dict) or catalog.get("edition") != edition:
        raise ValueError("Missing-word audit is not pinned to this original edition")
    prefix = catalog.get("word_id_prefix")
    digits = catalog.get("word_id_digits")
    reported_ids = source_absences.get("word_ids")
    evidence = source_absences.get("provenance")
    if (not isinstance(reported_ids, list) or not isinstance(evidence, list)
            or any(not isinstance(word, str) for word in reported_ids)):
        raise ValueError("Malformed source-word audit manifest")
    if reported_ids and not evidence:
        raise ValueError("Unattested word claims require source provenance")
    if len(set(reported_ids)) != len(reported_ids):
        raise ValueError("Duplicate source-unattested word ID")
    unattested = {}
    for word_id in sorted(reported_ids):
        if (not isinstance(word_id, str) or not isinstance(prefix, str)
                or not isinstance(digits, int) or isinstance(digits, bool)
                or len(word_id) != len(prefix) + digits
                or not word_id.startswith(prefix)
                or not word_id[len(prefix):].isascii()
                or not word_id[len(prefix):].isdigit()):
            raise ValueError(f"Invalid source-unattested word ID: {word_id!r}")
        key = f"{corpus}:{word_id}"
        if key not in candidates:
            raise ValueError(f"Unattested word not in source index: {key}")
        if any(field != "subject_referents" for _, field in candidates[key]):
            raise ValueError(f"Unattested word also has direct/pronominal claims: {key}")
        unattested[key] = {
            "source_edition": edition,
            "evidence": evidence,
            "source_claims": [{"entity_id": entity_id, "link_type": field}
                              for entity_id, field in sorted(candidates.pop(key))],
        }
    by_word = {
        word: [{"entity_id": entity_id, "link_type": field}
               for entity_id, field in sorted(hits)]
        for word, hits in sorted(candidates.items())
    }
    # Source may intentionally contain repeated indirect word groups.
    # Report raw assignments separately from distinct entity/field claims:
    # the inverse lookup necessarily collapses identical candidate pairs.
    unattested_raw_assignments = sum(
        1 for entity in entries
        for corpora in entity["occurrences"].values()
        for source_corpus, groups in corpora.items()
        for group in groups
        for word in group
        if f"{canonical_source_corpus(source_lock, source_corpus)}:{word}" in unattested
    )
    # This is an edition-specific source-WORD-INVENTORY compatibility
    # annotation, not a decision about canonical Bible versification or
    # which textual readings are genuine. Raw entity references stay intact.
    if source_verse_absences is None:
        source_verse_absences = {
            "schema_version": 1, "corpus": "sblgnt",
            "source_edition": source_lock["source_editions"]["sblgnt"]["edition"],
            "verse_ids": [], "provenance": [],
        }
    if type(source_verse_absences.get("schema_version")) is not int or source_verse_absences["schema_version"] != 1:
        raise ValueError("Unsupported absent-verse inventory schema")
    verse_corpus = source_verse_absences.get("corpus")
    verse_edition = source_verse_absences.get("source_edition")
    verse_catalog = source_lock["source_editions"].get(verse_corpus)
    if not isinstance(verse_catalog, dict) or verse_catalog.get("edition") != verse_edition:
        raise ValueError("Absent-verse inventory not pinned to this original edition")
    reported_verses = source_verse_absences.get("verse_ids")
    verse_evidence = source_verse_absences.get("provenance")
    if (not isinstance(reported_verses, list) or not isinstance(verse_evidence, list)
            or any(not isinstance(verse, str) for verse in reported_verses)):
        raise ValueError("Malformed absent-verse inventory manifest")
    if reported_verses and not verse_evidence:
        raise ValueError("Absent-verse inventory needs source audit provenance")
    if len(reported_verses) != len(set(reported_verses)):
        raise ValueError("Duplicate source-absent verse IDs")
    # An optional source-cited interpretive layer distinguishes an alternate
    # verse number from a textual-variant reading. No source references or
    # original words are reclassified or rewritten by this metadata.
    context_by_verse = {}
    if "verse_qualifications" in source_verse_absences:
        contexts = source_verse_absences["verse_qualifications"]
        if not isinstance(contexts, list):
            raise ValueError("Malformed source verse-qualification list")
        permitted = {
            "traditional_textual_variant_not_in_pinned_main_text",
            "doxology_in_edition_apparatus_not_main_word_inventory",
            "alternate_verse_number_for_final_benediction",
        }
        for context in contexts:
            if not isinstance(context, dict):
                raise ValueError("Invalid source verse-qualification record")
            verse = context.get("verse_id")
            explanation = context.get("explanation")
            evidence = context.get("evidence")
            classification = context.get("classification")
            if (not isinstance(verse, str)
                    or len(verse) != 8 or not verse.isascii() or not verse.isdigit()
                    or classification not in permitted
                    or not isinstance(explanation, str) or not explanation.strip()
                    or not isinstance(evidence, list) or len(evidence) < 2
                    or any(not isinstance(e, str) or not e.strip() for e in evidence)):
                raise ValueError(f"Invalid source verse-qualification evidence: {context!r}")
            if verse in context_by_verse:
                raise ValueError(f"Duplicate source verse qualification: {verse}")
            equivalent = context.get("equivalent_benediction_source_verse")
            if equivalent is not None:
                if (classification != "alternate_verse_number_for_final_benediction"
                        or not isinstance(equivalent, str)
                        or len(equivalent) != 8 or not equivalent.isascii() or not equivalent.isdigit()
                        or equivalent == verse or equivalent[:5] != verse[:5]):
                    raise ValueError(f"Invalid verse-number comparison: {verse}")
            if (classification == "alternate_verse_number_for_final_benediction"
                    and equivalent is None):
                raise ValueError(f"Missing benediction comparison verse: {verse}")
            context_by_verse[verse] = {
                "classification": classification,
                "explanation": explanation,
                "evidence": evidence,
            }
            if equivalent is not None:
                context_by_verse[verse]["equivalent_benediction_source_verse"] = equivalent
        if set(context_by_verse) != set(reported_verses):
            raise ValueError(
                f"Unqualified pinned source verses: "
                f"{sorted(set(reported_verses) - set(context_by_verse))}")
    unattested_verses = {}
    for verse in sorted(reported_verses):
        if not isinstance(verse, str) or len(verse) != 8 or not verse.isascii() or not verse.isdigit():
            raise ValueError(f"Malformed source-absent verse ID: {verse!r}")
        claims = [entry["id"] for entry in entries if verse in entry["references"]]
        if not claims:
            raise ValueError(f"Source-absent verse not referenced in derived index: {verse}")
        unattested_verses[f"{verse_corpus}:{verse}"] = {
            "source_edition": verse_edition,
            "source_reference_claims": claims,
            "evidence": verse_evidence,
            "scope": "absent_from_pinned_original_word_inventory_only",
            **({"source_context": context_by_verse[verse]}
               if verse in context_by_verse else {}),
        }
    # Reference claims without matching source-edition word anchors may derive
    # from textual variants, later epistle subscriptions or historical
    # identifications. Their reference lists stay exactly as imported.
    if reference_qualifications is None:
        reference_qualifications = {
            "schema_version": 1, "corpus": "sblgnt",
            "source_edition": source_lock["source_editions"]["sblgnt"]["edition"],
            "claims": [],
        }
    if type(reference_qualifications.get("schema_version")) is not int or reference_qualifications["schema_version"] != 1:
        raise ValueError("Unsupported reference-qualification schema")
    ref_corpus = reference_qualifications.get("corpus")
    ref_edition = reference_qualifications.get("source_edition")
    ref_catalog = source_lock["source_editions"].get(ref_corpus)
    if not isinstance(ref_catalog, dict) or ref_catalog.get("edition") != ref_edition:
        raise ValueError("Reference qualifications not pinned to original edition")
    claim_rows = reference_qualifications.get("claims")
    if not isinstance(claim_rows, list):
        raise ValueError("Malformed reference qualification claims")
    by_source_id = {entry["source_id"]: entry for entry in entries}
    qualified = defaultdict(list)
    seen_claims = set()
    allowed = {
        "textual_variant_name_not_in_pinned_edition",
        "traditional_subscription_candidate",
    }
    for claim in claim_rows:
        if not isinstance(claim, dict):
            raise ValueError("Malformed reference qualification claim")
        source_id, verse = claim.get("source_id"), claim.get("verse_id")
        cls, proof = claim.get("classification"), claim.get("evidence")
        if (not isinstance(source_id, str)
                or not isinstance(verse, str) or len(verse) != 8
                or not verse.isascii() or not verse.isdigit() or cls not in allowed
                or not isinstance(proof, list) or not proof
                or any(not isinstance(v, str) or not v.strip() for v in proof)):
            raise ValueError(f"Invalid reference qualification claim: {claim!r}")
        claim_key = (source_id, verse)
        if claim_key in seen_claims:
            raise ValueError(f"Duplicate reference qualification: {claim_key}")
        seen_claims.add(claim_key)
        entry = by_source_id.get(source_id)
        if entry is None:
            raise ValueError(f"Reference qualification points to absent index record: {source_id}")
        if verse not in entry["references"]:
            raise ValueError(f"Reference qualification has no source reference: {claim_key}")
        for field, corpora in entry["occurrences"].items():
            for raw_corpus, groups in corpora.items():
                if canonical_source_corpus(source_lock, raw_corpus) != ref_corpus:
                    continue
                for group in groups:
                    if any(word[1:9] == verse for word in group):
                        raise ValueError(
                            f"Reference qualification conflicts with exact original word "
                            f"anchor: {source_id} {verse} {field}")
        qualified[f"{ref_corpus}:{verse}"].append({
            "entity_id": entry["id"],
            "source_id": source_id,
            "source_edition": ref_edition,
            "classification": cls,
            "evidence": proof,
        })
    qualified = {
        ref: sorted(rows, key=lambda row: (row["entity_id"], row["source_id"]))
        for ref, rows in sorted(qualified.items())
    }
    return {
        "format": "bible-entity-index",
        "schema_version": 1,
        "provenance": {
            "source_repository": source_lock["source_repository"],
            "source_commit": source_lock["source_commit"],
            "source_snapshot_sha256": source_snapshot_sha256,
            "source_license": source_lock["source_license"],
            "source_credit": source_lock["source_credit"],
            "reviewed_hebrew_source": source_lock["reviewed_hebrew_source"],
            "reviewed_greek_source": source_lock["reviewed_greek_source"],
            "source_editions": source_lock["source_editions"],
            "source_corpora": source_lock["source_corpora"],
        },
        "statistics": {
            "source_records": source_record_count,
            "index_entities": len(entries),
            "quarantined_records": len(quarantined),
            "reviewed_entries": sum(e["review_status"] == "editorially_reviewed"
                                    for e in entries),
            "indexed_distinct_source_words": len(by_word),
            "unattested_distinct_source_words": len(unattested),
            "unattested_raw_word_assignments": unattested_raw_assignments,
            "unattested_source_verses": len(unattested_verses),
            "qualified_source_verse_contexts": len(context_by_verse),
            "unattested_source_verse_reference_claims": sum(
                len(x["source_reference_claims"])
                for x in unattested_verses.values()),
            "qualified_source_reference_claims": sum(
                len(rows) for rows in qualified.values()),
        },
        "quarantined": sorted(quarantined, key=lambda x: x["source_id"]),
        "entities": entries,
        "by_word": by_word,
        "unattested_source_words": unattested,
        "unattested_source_verses": unattested_verses,
        "qualified_source_references": qualified,
    }
