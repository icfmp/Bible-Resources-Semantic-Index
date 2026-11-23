#!/usr/bin/env python3
"""Strict source-qualified disposition for inherited biblical-place constructs.

These 27 imported ACAI identities are *not* all literal toponyms in WLC.
An attested word for a tribe, person, direction or gentilic is NOT automatic
evidence of a distinct city. Never add a word link to make a census shrink.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    "historical_regional_crossname",
    "contested_toponym",
    "demonym_inferred_locality",
    "ethnonymic_political_area",
    "ambiguous_gentilic",
    "directional_gatekeeper_post",
    "historical_regnal_area",
    "poetic_cosmic_geography",
    "derived_tribal_allotment",
}
ACTIONS = {
    "derived_tribal_allotment": "classify_biblical_tribal_allotment_not_province",
    "ambiguous_gentilic": "qualify_inferred_geographical_identity",
    "directional_gatekeeper_post": "qualify_inferred_geographical_identity",
}
EXPECTED_BASE = "de3c285b3722cad8cf6aa699951648c5e39c1e7d"


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def native_current_unanchored_places(data: Path) -> set[str]:
    """Compute the census rather than suppressing it after a review."""
    result = set()
    for path in (data / "entities" / "places").glob("*.json"):
        row = load(path)
        if row.get("mentioned_in_bible") is True and not row.get("references") and not row.get("explicit_instances"):
            result.add(row["bsi"]["source_id"])
    return result


def check_receipt(record: dict, item: dict) -> None:
    sid = item["source_id"]
    action = item.get("required_receipt_action")
    require(action == ACTIONS.get(item["attestation_class"]),
            sid + ": correction action does not match independent place classification")
    require(record["bsi"].get("review_status") == "editorially_reviewed",
            sid + ": corrected record lacks native editorial approval")
    receipts = [r for r in record["bsi"].get("editorial_field_changes", [])
                if r.get("action") == action]
    require(len(receipts) == 1, sid + ": no unique correction receipt")
    receipt = receipts[0]
    require(len(receipt.get("reason", "")) >= 100
            and isinstance(receipt.get("evidence"), list)
            and bool(receipt["evidence"]),
            sid + ": undocumented native source field change")
    before = receipt.get("replaced_field_values", {}).get("before")
    after = receipt.get("replaced_field_values", {}).get("after")
    require(isinstance(before, dict) and isinstance(after, dict)
            and before and set(before) == set(after) and before != after,
            sid + ": nonreversible source edit")
    for field, value in after.items():
        actual = record["localizations"]["eng"].get(field) if field in {
            "preferred_label", "alternate_labels"} else record.get(field)
        require(actual == value, sid + ": corrected field has drifted")
    if action == "classify_biblical_tribal_allotment_not_province":
        require(before == {"place_types": {"acai": ["province"]}}
                and after == {"place_types": {"acai": ["tribal territory"]}},
                sid + ": inaccurate source/tribal administrative category or missing original")
    if action == "qualify_inferred_geographical_identity":
        require(set(before) == {"preferred_label"} and
                "(inferred)" in record["localizations"]["eng"]["preferred_label"]
                if item["attestation_class"] == "directional_gatekeeper_post"
                else set(before) == {"preferred_label"} and
                "(possible place of origin)" in record["localizations"]["eng"]["preferred_label"],
                sid + ": speculative place label presented as verified")


def read_pinned_words(paths: dict[str, Path], ids: set[str]) -> dict[str, dict]:
    found = {}
    for corpus in ("wlc", "sblgnt"):
        path = paths[corpus]
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, delimiter="\t")
            require({"xml:id", "english", "gloss", "lemma"}.issubset(reader.fieldnames or []),
                    "Invalid source-locked original word inventory")
            for item in reader:
                wid = item["xml:id"]
                if wid in ids:
                    require(wid not in found, "Duplicate original source witness: " + wid)
                    require((corpus == "wlc" and wid.startswith("o")) or
                            (corpus == "sblgnt" and wid.startswith("n")),
                            "Original witness in wrong edition: " + wid)
                    found[wid] = item
    require(set(found) == ids, "Quoted exact original-language word missing from pinned source inventory")
    return found


def validate(data: Path, ledger_path: Path, wlc: Path | None = None,
             sblgnt: Path | None = None) -> dict:
    docket = load(ledger_path)
    lock = load(data / "source.lock.json")
    require(docket.get("schema_version") == 1
            and docket.get("baseline_commit") == EXPECTED_BASE,
            "Unverifiable frozen place cohort baseline")
    require(docket.get("source_editions") == {
        "wlc": lock["source_editions"]["wlc"]["edition"],
        "sblgnt": lock["source_editions"]["sblgnt"]["edition"],
    }, "Source edition differs from locked Hebrew/Greek originals")
    cases = docket.get("cases")
    require(isinstance(cases, list) and cases, "Source-place audit docket empty")
    ids = [c.get("source_id") for c in cases]
    require(len(set(ids)) == len(ids), "Duplicate source-place editorial decision")
    require(set(ids) == native_current_unanchored_places(data),
            "A Bible-marked unanchored place was omitted, added, or reclassified without updated evidence")
    words = {}
    result = Counter()
    for case in cases:
        sid = case["source_id"]
        require(isinstance(sid, str) and re.fullmatch(r"place:[A-Za-z0-9_.-]+", sid),
                "Invalid imported place source ID")
        name = sid.split(":", 1)[1]
        row = load(data / "entities" / "places" / (name + ".json"))
        require(row["bsi"].get("source_id") == sid and row["id"] == sid
                and re.fullmatch(r"[a-f0-9]{64}", row["bsi"].get("source_sha256", "")),
                sid + ": original ACAI source identity/fingerprint replaced")
        require(case.get("attestation_class") in CATEGORIES,
                sid + ": unknown editorial relationship to Hebrew/Greek original")
        require(case.get("outcome") in {"corrected", "contextual_qualified"},
                sid + ": unresolved or falsely certified status")
        original = case.get("original_key_verses")
        require(isinstance(original, list) and original == row["key_references"]
                and len(original) == len(set(original)),
                sid + ": key references changed without frozen source qualification")
        require(case.get("qualification") and
                isinstance(case["qualification"], str) and len(case["qualification"]) > 125,
                sid + ": missing historically precise editorial analysis")
        url = case.get("independent_source_url")
        require(isinstance(url, str) and url.startswith("https://") and " " not in url,
                sid + ": missing independently accessible source context")
        is_construct = case["attestation_class"] == "derived_tribal_allotment"
        require(is_construct == (name.startswith("TerritoryOf")),
                sid + ": invented territory class or unmatched tribal construction")
        if is_construct:
            require(original == [] and row["place_types"]["acai"] == ["tribal territory"],
                    sid + ": biblical tribal allotment is still named a province")
        else:
            require(bool(original), sid + ": contextual identity without inherited source keys")
        evidence = case.get("exact_pinned_word_witnesses")
        require(isinstance(evidence, list) and bool(evidence),
                sid + ": no real original-language witness")
        seen = set()
        for witness in evidence:
            wid, verse = witness.get("word_id"), witness.get("verse_id")
            require(isinstance(wid, str) and
                    re.fullmatch(r"(o[0-9]{12}|n[0-9]{11})", wid) and
                    verse == wid[1:9] and wid not in seen,
                    sid + ": missing or malformed/duplicate original word identity")
            seen.add(wid)
            require((verse[:2] == "06" if is_construct else verse in original),
                    sid + ": unsupported source verse, cannot infer original place name")
            require(witness.get("english") is not None and
                    isinstance(witness.get("gloss"), str) and
                    isinstance(witness.get("lemma"), str) and
                    witness["lemma"].strip(),
                    sid + ": incomplete token-specific source proof")
            words[wid] = witness
        if case["outcome"] == "corrected":
            check_receipt(row, case)
        else:
            require("required_receipt_action" not in case and
                    case["attestation_class"] not in ACTIONS,
                    sid + ": contextual verification conceals an unreviewed correction")
        result[case["attestation_class"]] += 1
        result[case["outcome"]] += 1
    if (wlc is None) != (sblgnt is None):
        raise ValueError("Both exact pinned edition TSV paths are required together")
    if wlc is not None:
        pinned = read_pinned_words({"wlc": wlc, "sblgnt": sblgnt}, set(words))
        for wid, proof in words.items():
            for field in ("english", "gloss", "lemma"):
                require(proof[field] == pinned[wid][field],
                        f"Original source token was misquoted or reassigned: {wid} {field}")
    return {"total": len(cases), "corrected": result["corrected"],
            "contextual_qualified": result["contextual_qualified"],
            "distinct_original_words": len(words),
            "categories": {k: result[k] for k in sorted(CATEGORIES) if result[k]}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--ledger", type=Path,
                        default=Path("data/source-place-attestation-review.json"))
    parser.add_argument("--wlc", type=Path)
    parser.add_argument("--sblgnt", type=Path)
    options = parser.parse_args()
    print("BRSi_PLACE_SOURCE_REVIEW " + json.dumps(
        validate(options.data, options.ledger, options.wlc, options.sblgnt), sort_keys=True))


if __name__ == "__main__":
    main()
