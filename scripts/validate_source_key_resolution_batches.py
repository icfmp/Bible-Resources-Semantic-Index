#!/usr/bin/env python3
"""Generic, repeatable proof validation for independently adjudicated source-key batches.

This is intentionally independent of the count in any one milestone.
A selected/triaged case never counts as resolved; only a source-backed
verified-correct determination or a separately proven reversible edit does.
The original Bible/ACAI/Macula snapshots are not modified.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from validate_resolved_source_keys import require_real_receipt, source_history

KIND_DIR = {
    "deity": "deities", "fauna": "fauna", "flora": "flora",
    "group": "groups", "person": "people", "place": "places", "realia": "realia",
}
PIN_IDS = {"wlc": re.compile(r"o[0-9]{12}\Z"),
           "sblgnt": re.compile(r"n[0-9]{11}\Z")}
BCV = re.compile(r"[0-9]{8}\Z")
RELATIONS = {
    "verified_error_corrected",
    "linked_original_witness_in_adjacent_context",
    "independently_correlated_historical_or_narrative_context",
}


def check(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_words(record: dict) -> set[str]:
    return {
        w for field in ("explicit_instances", "pronominal_referents", "subject_referents")
        for groups in record.get(field, {}).values()
        for group in groups for w in group
    }


def inspect_metadata(
    data: Path, ledger: dict, candidates: dict,
    previous: dict, original_queue: dict,
) -> tuple[dict, dict[str, set[str]]]:
    check(ledger.get("schema_version") == 2,
          "Expected generic source resolution batch schema v2")
    lock = read(data / "source.lock.json")
    check(ledger.get("source_pins") == {
        corpus: lock["source_editions"][corpus]["edition"]
        for corpus in ("wlc", "sblgnt")
    }, "Original-language source edition pins must exactly match input lock")
    check(isinstance(ledger.get("policy"), str) and len(ledger["policy"]) >= 90,
          "Source editorial decision policy must be explicit")
    candidates_list = candidates.get("cases")
    decisions = ledger.get("cases")
    check(isinstance(candidates_list, list) and bool(candidates_list),
          "Missing selected source queue")
    check(isinstance(decisions, list) and len(decisions) == len(candidates_list),
          "Resolution count differs from selected independent queue")
    selected = {c["source_id"]: c["key_verses"] for c in candidates_list}
    check(len(selected) == len(candidates_list), "Duplicate source identity in selection")
    pool = {c["source_id"]: c["key_verses"] for c in original_queue["cases"]}
    check(len(pool) == len(original_queue["cases"]),
          "Duplicate source identity in original queue")
    check(all(source_id in pool and verses == pool[source_id]
              for source_id, verses in selected.items()),
          "Selected cases do not match original unresolved queue")
    prior = set(c["source_id"] for c in previous["cases"])
    check(len(prior) == len(previous["cases"]),
          "Previous resolution register duplicates identities")
    check(not prior.intersection(selected),
          "Previously finalized cases cannot be counted twice")
    seen = set()
    targets_requested = set()
    words_requested = defaultdict(set)
    summary = Counter()
    for case in decisions:
        source_id = case.get("source_id")
        check(isinstance(source_id, str) and source_id not in seen
              and source_id in selected, f"Unknown/duplicate identity {source_id!r}")
        seen.add(source_id)
        kind, name = source_id.split(":", 1)
        check(kind in KIND_DIR and name and "/" not in name and ".." not in name,
              f"Unsafe identity path {source_id}")
        path = data / "entities" / KIND_DIR[kind] / (name + ".json")
        check(path.is_file(), f"Record missing: {source_id}")
        record = read(path)
        bsi = record["bsi"]
        check(record["id"] == source_id and bsi["source_id"] == source_id
              and re.fullmatch(r"[a-f0-9]{64}", bsi["source_sha256"]) is not None,
              f"Identity or original SHA fingerprint altered: {source_id}")
        outcome = case.get("outcome")
        check(outcome in {"corrected", "verified_correct"},
              f"Triaged/uncertain is not resolved: {source_id}")
        summary[outcome] += 1
        target_keys = case.get("target_key_verses")
        check(target_keys == selected[source_id]
              and all(BCV.fullmatch(v) for v in target_keys),
              f"Historical key targets changed or malformed: {source_id}")
        check(set(target_keys).issubset(source_history(record)),
              f"Historical source key missing without documented before/after: {source_id}")
        explanation = case.get("editorial_explanation")
        check(isinstance(explanation, str) and len(explanation) >= 95,
              f"Source-specific editorial conclusion missing: {source_id}")
        evidence = case.get("source_evidence")
        check(isinstance(evidence, list) and len(evidence) == len(target_keys),
              f"Each historical key requires a decision: {source_id}")
        if outcome == "corrected":
            action = case.get("required_receipt_action")
            check(isinstance(action, str) and action,
                  f"Correction missing a reversible receipt action: {source_id}")
            require_real_receipt(record, action, source_id)
            receipts = [x for x in bsi.get("editorial_field_changes", [])
                        if x["action"] == action]
            before = receipts[0]["replaced_field_values"]["before"]
            after = receipts[0]["replaced_field_values"]["after"]
            check("key_references" in before and "key_references" in after
                  and before["key_references"] != after["key_references"],
                  f"Claimed correction did not actually change a key: {source_id}")
            check(any(v in before["key_references"]
                      and v not in after["key_references"] for v in target_keys),
                  f"Corrected case has no proven rejected old key: {source_id}")
        else:
            check("required_receipt_action" not in case,
                  f"Correct-as-is case cannot pretend to have an edit: {source_id}")
            check(set(target_keys).issubset(record["key_references"]),
                  f"Correct-as-is source keys were secretly changed: {source_id}")
        word_ids = source_words(record)
        seen_keys = set()
        for proof in evidence:
            key = proof.get("original_key_verse")
            check(key in target_keys and key not in seen_keys,
                  f"Duplicate/missing per-key evidence: {source_id}/{key}")
            seen_keys.add(key)
            witness = proof.get("pinned_witness_word_id")
            check(isinstance(witness, str)
                  and any(pattern.fullmatch(witness) for pattern in PIN_IDS.values()),
                  f"Fake original word syntax: {source_id}/{key}")
            corpus = "wlc" if witness.startswith("o") else "sblgnt"
            book = int(witness[1:3])
            check((1 <= book <= 39 if corpus == "wlc" else 40 <= book <= 66),
                  f"Impossible source book for word {witness}")
            check(proof.get("pinned_witness_verse") == witness[1:9]
                  and witness in word_ids,
                  f"Witness absent from *this* record's original word links: {source_id}/{witness}")
            check(proof.get("relation") in RELATIONS
                  and isinstance(proof.get("nearby_native_source_word"), bool),
                  f"Unsubstantiated direct/contextual semantic relation: {source_id}")
            if proof["nearby_native_source_word"]:
                check(witness[1:6] == key[:5]
                      and -2 <= int(witness[6:9]) - int(key[5:8]) <= 3,
                      f"Claimed neighboring witness is not in target passage: {source_id}")
            elif outcome == "verified_correct":
                check(proof["relation"] ==
                      "independently_correlated_historical_or_narrative_context",
                      f"Non-nearby no-edit verdict requires explicit independent context: {source_id}")
            if outcome == "corrected":
                check(proof["relation"] == "verified_error_corrected",
                      f"Correction evidence improperly described as unaltered: {source_id}")
            elif proof["relation"] == "verified_error_corrected":
                raise ValueError(f"{source_id}: no-change evidence cannot describe an edit")
            excerpt = proof.get("target_original_english_excerpt")
            check(isinstance(excerpt, str) and len(excerpt) >= 1
                  and len(excerpt) <= 230,
                  f"Missing concise original-source passage evidence: {source_id}/{key}")
            reason = proof.get("explanation")
            check(isinstance(reason, str) and len(reason) >= 90,
                  f"No verse-specific original source/identity explanation: {source_id}/{key}")
            targets_requested.add(key)
            words_requested[corpus].add(witness)
        check(len(seen_keys) == len(target_keys),
              f"Each source key needs exactly one signed decision: {source_id}")
    check(seen == set(selected), "Some selected identities were not settled")
    return ({
        "resolved": len(decisions),
        "corrected": summary["corrected"],
        "verified_correct": summary["verified_correct"],
        "prior_resolved": len(prior),
        "remaining_outstanding_from_snapshot": len(pool) - len(selected),
        "distinct_source_witness_words": sum(len(words) for words in words_requested.values()),
    }, {"verses": targets_requested, **words_requested})


def verify_pinned_originals(
    evidence: list[dict], needed: dict[str, set[str]], pinned: dict[str, Path],
) -> None:
    expected_words = needed
    actual_verses = defaultdict(list)
    for corpus, path in pinned.items():
        found = set()
        with path.open(encoding="utf-8-sig", newline="") as inp:
            reader = csv.DictReader(inp, delimiter="\t")
            check({"xml:id", "english", "gloss", "text"}.issubset(reader.fieldnames or []),
                  f"Pinned original TSV is missing required source fields: {path}")
            for row in reader:
                wid = row["xml:id"]
                if wid in expected_words[corpus]:
                    check(wid not in found, f"Duplicate pinned original word ID {wid}")
                    found.add(wid)
                if wid[1:9] in expected_words["verses"]:
                    actual_verses[wid[1:9]].append(
                        (row["english"] or row["gloss"] or row["text"]).replace(" ", "_"))
        check(found == expected_words[corpus],
              f"Unknown original source word IDs for {corpus}: "
              f"{sorted(expected_words[corpus] - found)}")
    no_word = "(No word in the edition at this key verse; examine the editorial correction receipt.)"
    for case in evidence:
        for proof in case["source_evidence"]:
            target = proof["original_key_verse"]
            full = " ".join(actual_verses.get(target, []))
            expected_excerpt = full[:230] if full else no_word
            check(expected_excerpt == proof["target_original_english_excerpt"],
                  f"{case['source_id']}: quoted target passage differs from locked source at {target}")


def validate(data: Path, ledger_path: Path, select_path: Path,
             previous_path: Path, pool_path: Path,
             pinned: dict[str, Path] | None = None) -> dict:
    ledger = read(ledger_path)
    check(ledger.get("candidates_file") == select_path.as_posix()
          or ledger.get("candidates_file") == str(select_path.relative_to(data.parent)),
          "Resolution must name its actual selected source queue")
    check(ledger.get("previous_resolution_file") == previous_path.as_posix()
          or ledger.get("previous_resolution_file") == str(previous_path.relative_to(data.parent)),
          "Resolution must reference preceding certification ledger")
    stats, requested = inspect_metadata(
        data, ledger, read(select_path), read(previous_path), read(pool_path))
    if pinned is not None:
        check(set(pinned) == {"wlc", "sblgnt"},
              "Both pinned source editions are needed for proof verification")
        verify_pinned_originals(ledger["cases"], requested, pinned)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--previous", type=Path, required=True)
    ap.add_argument("--pool", type=Path, required=True)
    ap.add_argument("--wlc", type=Path)
    ap.add_argument("--sblgnt", type=Path)
    a = ap.parse_args()
    if (a.wlc is None) != (a.sblgnt is None):
        ap.error("Locked WLC and SBLGNT must be supplied together")
    pinned = None if a.wlc is None else {"wlc": a.wlc, "sblgnt": a.sblgnt}
    report = validate(a.data, a.ledger, a.selection, a.previous, a.pool, pinned)
    print("BRSI_VERIFIED_SOURCE_KEY_BATCH " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
