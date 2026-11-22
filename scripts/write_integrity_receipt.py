#!/usr/bin/env python3
"""Write deterministic SHA-256 receipts for locally built BSI index inputs.

This records *file-byte integrity*, not licensing approval, source-equivalence,
editorial validation, or permission to release. No network or publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def receipt(files: dict[str, Path]) -> dict:
    if not files:
        raise ValueError("At least one file is required")
    result = {}
    for name, path in sorted(files.items()):
        if not path.is_file():
            raise FileNotFoundError(path)
        h = hashlib.sha256()
        size = 0
        with path.open("rb") as src:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                h.update(chunk)
                size += len(chunk)
        result[name] = {"sha256": h.hexdigest(), "bytes": size}
    return {"schema_version": 1, "scope": "local_build_file_integrity_only",
            "files": result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity", type=Path, required=True,
                        help="Exact output of the current native entity build")
    parser.add_argument("--greek", type=Path, required=True,
                        help="Greek index file to identify, not to approve")
    parser.add_argument("--hebrew", type=Path, required=True,
                        help="Hebrew index file to identify, not to approve")
    parser.add_argument("--output", type=Path, help="Receipt JSON; stdout if absent")
    args = parser.parse_args()
    result = receipt({"entity": args.entity, "greek": args.greek,
                      "hebrew": args.hebrew})
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
