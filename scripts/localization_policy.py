#!/usr/bin/env python3
"""Fail-closed access to unreviewed inherited localization fields.

Source text remains unchanged in native records. This policy is for future
reader-facing projections, not for changing the historical ACAI witness.
"""
from __future__ import annotations

import copy

FIELDS = frozenset({"descriptions", "preferred_label", "alternate_labels"})
HOLD_STATUS = "withheld_pending_review"


def validated_holds(record: dict) -> frozenset[str]:
    """Validate and return explicitly withheld field selectors.

    Unknown or malformed policy metadata must fail rather than silently allow
    reader-facing content. A global selector applies across all languages.
    """
    meta = record.get("bsi", {})
    if not isinstance(meta, dict):
        raise ValueError("Invalid BRSI metadata")
    policy = meta.get("inherited_localizations")
    if policy is None:
        return frozenset()
    if not isinstance(policy, dict) or policy.get("status") != HOLD_STATUS:
        raise ValueError("Unknown inherited localization review status")
    if policy.get("source") != "acai":
        raise ValueError("Missing inherited localization provenance")
    reason = policy.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Missing inherited localization review reason")
    fields = policy.get("fields")
    if not isinstance(fields, list) or not fields or any(
        not isinstance(field, str) or not field.strip() for field in fields
    ):
        raise ValueError("Missing inherited localization review fields")
    if len(fields) != len(set(fields)):
        raise ValueError("Duplicate inherited localization review fields")
    for selector in fields:
        pieces = selector.split(".")
        if not (len(pieces) == 1 and pieces[0] in FIELDS
                or len(pieces) == 2 and len(pieces[0]) == 3
                and pieces[0].isalpha() and pieces[0].islower()
                and pieces[1] in FIELDS):
            raise ValueError(f"Unknown inherited localization selector: {selector}")
    return frozenset(fields)


def reader_field(record: dict, language: str, field: str):
    """Return a source-unreviewed field or None if held/unavailable.

    Never claims editorial approval: the caller must retain the returned
    provenance status. Withheld values are not copied to the result.
    """
    if not isinstance(language, str) or len(language) != 3 or not language.isalpha() or not language.islower():
        raise ValueError("Expected a three-letter lowercase language tag")
    if field not in FIELDS:
        raise ValueError(f"Unsupported reader-facing localization field: {field}")
    held = validated_holds(record)
    if field in held or f"{language}.{field}" in held:
        return None
    localizations = record.get("localizations", {})
    if not isinstance(localizations, dict):
        raise ValueError("Invalid localizations")
    localized = localizations.get(language, {})
    if not isinstance(localized, dict):
        raise ValueError("Invalid language localization")
    value = localized.get(field)
    if value is None:
        return None
    if field == "preferred_label":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid preferred label")
    elif not isinstance(value, list):
        raise ValueError(f"Invalid {field} list")
    return {"value": copy.deepcopy(value), "language": language,
            "field": field, "review_status": "source_unreviewed",
            "source_id": record["bsi"]["source_id"]}
