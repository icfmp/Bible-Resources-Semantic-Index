#!/usr/bin/env python3
"""Validate independent ACAI/BRSI reference fields without rewriting source.

Both references and key_references contain Copenhagen Alliance ORG BCV8
identifiers. Original ACAI docs describe their format but do not state that
key_references are a subset of references. Do not infer missing witnesses.
"""
from __future__ import annotations

import re

BCV8 = re.compile(r"[0-9]{8}\Z")


def validate_reference_fields(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("BRSI entity must be an object")
    for field in ("references", "key_references"):
        refs = record.get(field)
        if not isinstance(refs, list):
            raise ValueError(f"{field} must be a present BCV8 list")
        for index, value in enumerate(refs):
            if not isinstance(value, str) or BCV8.fullmatch(value) is None:
                raise ValueError(f"{field}[{index}] is not an ORG BCV8 string: {value!r}")
    # No automatic normalization, deduplication or canonical versification
    # conversion. A key verse may intentionally lack a direct word witness.
