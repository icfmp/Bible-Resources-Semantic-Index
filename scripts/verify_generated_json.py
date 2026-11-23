#!/usr/bin/env python3
"""Fail closed when a regenerated JSON resource differs from its committed baseline.

Use for source-pinned BRSI resource reconstruction. This is a source-neutral,
read-only structural identity guard, not textual/semantic certification,
release authorization or a replacement for original-source checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field {key!r}")
        result[key] = value
    return result


def nonstandard_constant(value):
    raise ValueError(f"Non-standard JSON constant {value}")


def decode(raw: bytes, label: str):
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_pairs,
            parse_constant=nonstandard_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid strict JSON: {exc}") from exc


def canonical(data) -> bytes:
    """Compare types and values, independent of whitespace and object key order."""
    return json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def verify(generated: Path, baseline: Path) -> dict:
    generated = Path(generated)
    baseline = Path(baseline)
    if not generated.is_file():
        raise ValueError(f"Missing generated JSON: {generated}")
    if not baseline.is_file():
        raise ValueError(f"Missing committed baseline JSON: {baseline}")
    if generated.resolve() == baseline.resolve():
        raise ValueError("Generated input and committed baseline must be different files")
    generated_raw = generated.read_bytes()
    baseline_raw = baseline.read_bytes()
    actual = canonical(decode(generated_raw, str(generated)))
    original = canonical(decode(baseline_raw, str(baseline)))
    if actual != original:
        raise ValueError(
            "Source-pinned generated JSON differs from committed baseline: "
            f"{generated} != {baseline}; "
            f"generated canonical SHA-256={hashlib.sha256(actual).hexdigest()}, "
            f"baseline canonical SHA-256={hashlib.sha256(original).hexdigest()}"
        )
    return {
        "status": "identical_strict_json_values",
        "generated_sha256": hashlib.sha256(generated_raw).hexdigest(),
        "baseline_sha256": hashlib.sha256(baseline_raw).hexdigest(),
        "canonical_sha256": hashlib.sha256(actual).hexdigest(),
        "publication_approved": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.generated, args.baseline)
    except (ValueError, OSError) as exc:
        print(f"BRSI_JSON_BASELINE_FAILURE: {exc}", file=sys.stderr)
        return 1
    print("BRSI_JSON_BASELINE_IDENTICAL", json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
