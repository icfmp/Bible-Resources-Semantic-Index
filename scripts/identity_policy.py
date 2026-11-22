#!/usr/bin/env python3
"""Minimal, reviewed human disambiguation for an index identity.

Identity hints are optional internal identification aids, not biographies,
localized display copy or asserted cross-resource equivalences.
"""
from __future__ import annotations

import re

VERSE_ID = re.compile(r"^[0-9]{8}$")
KEYS = frozenset({"name", "qualifier", "language", "evidence_references", "review_status"})


def validate_identity_hint(record: dict) -> None:
    metadata = record.get("bsi", {})
    if not isinstance(metadata, dict):
        raise ValueError("Invalid BRSI metadata")
    hint = metadata.get("identity_hint")
    if hint is None:
        return
    if not isinstance(hint, dict) or set(hint) != KEYS:
        raise ValueError("Identity hint has missing or unexpected fields")
    if hint["language"] != "eng" or hint["review_status"] != "editorially_reviewed":
        raise ValueError("Identity hint must be reviewed in the single working language")
    for field, size in (("name", 80), ("qualifier", 140)):
        value = hint[field]
        if not isinstance(value, str) or not value.strip() or len(value) > size or "\n" in value:
            raise ValueError(f"Identity hint {field} must be short, nonempty, and single-line")
    if hint["name"].strip().lower() == hint["qualifier"].strip().lower():
        raise ValueError("Identity qualifier must distinguish, not repeat, the name")
    references = hint["evidence_references"]
    if not isinstance(references, list) or not references or any(
        not isinstance(ref, str) or not VERSE_ID.fullmatch(ref) for ref in references
    ):
        raise ValueError("Identity hint requires exact eight-digit verse references")
    if len(set(references)) != len(references):
        raise ValueError("Identity hint references must be unique")
    if not set(references).issubset(record.get("references", [])):
        raise ValueError("Identity hint evidence must occur in source-record references")
