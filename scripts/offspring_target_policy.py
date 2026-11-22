#!/usr/bin/env python3
"""Reject untyped family descendant targets without guessing the correct ID.

An offspring list may point to a person or to a collective group, so it must
not be forced into a person-only schema. Full target resolution remains the
responsibility of the existing exact relationship graph audit.
"""
from __future__ import annotations

import re

TYPED_ENTITY_ID = re.compile(r"[A-Za-z][A-Za-z_-]*:[^\s:]+\Z")


def validate_offspring_targets(record: dict) -> None:
    if "offspring" not in record:
        return
    values = record["offspring"]
    if not isinstance(values, list):
        raise ValueError("offspring must be a list of typed BRSI entity IDs")
    for index, target in enumerate(values):
        if not isinstance(target, str) or not TYPED_ENTITY_ID.fullmatch(target):
            raise ValueError(
                f"offspring[{index}] must be a typed entity ID, not a source label: {target!r}")
