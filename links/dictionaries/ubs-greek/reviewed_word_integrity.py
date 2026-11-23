#!/usr/bin/env python3
"""Reusable original-word integrity guard for reviewed Greek lexical batches.

This is a source-specific *mechanical* invariant, not an editorial decision.
A separately reviewed ledger and each batch's source/grammar/Strong checks
must authorize every word ID before this code may relabel its match status.
Never select a lexical entry, infer a UBS LEXID, or change original material.
"""
from __future__ import annotations

import copy

# Field names belong to the pinned source-specific Greek word evidence schema.
# These are copied verbatim from the independently rebuilt source witnesses.
WITNESS_FIELDS = (
    ("original_lemma", "original_lemma"),
    ("original_strong", "original_strong"),
    ("original_ln", "original_ln"),
    ("original_reference", "reference"),
    ("original_class", "original_class"),
    ("original_morph", "original_morph"),
    ("corroborating_ubs_ln_codes", "attested_headword_ln_codes"),
)


def verify_original_word(record, witness, word_id, entry_id, pending_status):
    """Fail on any original annotation or pre-review identity mismatch."""
    if not isinstance(word_id, str) or not word_id:
        raise ValueError("Original Greek word-ID missing")
    if not isinstance(record, dict) or not isinstance(witness, dict):
        raise ValueError("Original Greek reviewed word witness missing: " + word_id)
    expected = {
        "entry_id": entry_id,
        "match_type": pending_status,
        **{target: witness[source] for target, source in WITNESS_FIELDS},
    }
    for field, value in expected.items():
        if (field not in record or type(record[field]) is not type(value)
                or record[field] != value):
            raise ValueError(
                "Original Greek reviewed word witness drift at "
                + word_id + ": " + field
            )


def apply_review_status(candidate, approved_ids, pending_status, reviewed_status):
    """Return a deep-copied candidate with *only* approved statuses changed.

    No new/deleted word, annotation, inherited editorial decision, Strong map,
    source revision, publication flag, or any other top-level field can change.
    Every approved ID must already exist with the previous *unapproved* status.
    """
    if (not isinstance(pending_status, str) or not pending_status
            or not isinstance(reviewed_status, str) or not reviewed_status
            or pending_status == reviewed_status):
        raise ValueError("Original Greek review status transition malformed")
    selected = tuple(approved_ids)
    selected_ids = set(selected)
    if not selected or len(selected_ids) != len(selected):
        raise ValueError("Original Greek reviewed word set empty or duplicated")
    rows = candidate["by_macula_word"]
    if not isinstance(rows, dict) or not selected_ids.issubset(rows):
        raise ValueError("Original Greek approved word ID absent from source overlay")
    for wid in selected_ids:
        if rows[wid].get("match_type") != pending_status:
            raise ValueError("Greek word already reviewed or not pending: " + wid)
    output = copy.deepcopy(candidate)
    for wid in selected_ids:
        output["by_macula_word"][wid]["match_type"] = reviewed_status
    if set(output) != set(candidate) or set(output["by_macula_word"]) != set(rows):
        raise ValueError("Original Greek lexical overlay structure changed")
    for key, original in candidate.items():
        if key != "by_macula_word" and output[key] != original:
            raise ValueError("Frozen Greek lexical source or editorial metadata changed")
    for wid, original in rows.items():
        updated = output["by_macula_word"][wid]
        if (set(original) != set(updated)
                or any(original[k] != updated[k] for k in original if k != "match_type")
                or (wid not in selected_ids and original != updated)
                or (wid in selected_ids and updated["match_type"] != reviewed_status)):
            raise ValueError("Original Greek lexical word annotation altered: " + wid)
    return output
