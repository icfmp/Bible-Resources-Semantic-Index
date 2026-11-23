#!/usr/bin/env python3
"""Strict, source-pinned certification of editorially *resolved* key-verse cases.

A classified/reviewed case is not resolved. A resolved case must either have a
real, reasoned and reversible data correction or independently verified,
original-word-backed contextual/indirect/derived evidence justifying no edit.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

KIND_DIR = {
    "deity": "deities", "fauna": "fauna", "flora": "flora",
    "group": "groups", "person": "people", "place": "places",
    "realia": "realia",
}
BCV8 = re.compile(r"[0-9]{8}\Z")
PINNED_ID = {"wlc": re.compile(r"o[0-9]{12}\Z"),
             "sblgnt": re.compile(r"n[0-9]{11}\Z")}
EDIT_FIELDS = {
    "references", "key_references", "explicit_instances",
    "alternate_labels", "preferred_label", "group_origin",
    "mentioned_in_bible", "non_biblical",
}


def check(ok: bool, msg: str) -> None:
    if not ok:
        raise ValueError(msg)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_history(record: dict) -> set[str]:
    historical = set(record["key_references"])
    for receipt in record["bsi"].get("editorial_field_changes", []):
        field_change = receipt.get("replaced_field_values", {})
        for v in ("before", "after"):
            historical.update(field_change.get(v, {}).get("key_references", []))
    return historical


def require_real_receipt(record: dict, action: str, source_id: str) -> None:
    check(record["bsi"].get("review_status") == "editorially_reviewed",
          f"{source_id}: unreviewed entity claimed corrected")
    receipts = [
        x for x in record["bsi"].get("editorial_field_changes", [])
        if x.get("action") == action
    ]
    check(len(receipts) == 1,
          f"{source_id}: missing/duplicate source-specific correction {action}")
    x = receipts[0]
    check(isinstance(x.get("reason"), str) and len(x["reason"]) >= 55,
          f"{source_id}: insufficient specific editorial reason")
    check(isinstance(x.get("evidence"), list) and bool(x["evidence"]),
          f"{source_id}: no source evidence for claimed correction")
    changes = x.get("replaced_field_values", {})
    before, after = changes.get("before"), changes.get("after")
    check(isinstance(before, dict) and isinstance(after, dict)
          and before != after, f"{source_id}: no real changed field")
    check(set(before) == set(after) and set(after) & EDIT_FIELDS,
          f"{source_id}: incomplete/reversibility-defeating before/after receipt")
    # Every reported value must either persist now or be accounted for by a
    # later, separately reasoned edit. Do not require the old receipt to be
    # the last one on a record after subsequent independent corrections.
    all_receipts = record["bsi"]["editorial_field_changes"]
    index = all_receipts.index(x)
    for key, expected in after.items():
        current = record.get(key)
        if key == "alternate_labels":
            current = record.get("localizations", {}).get("eng", {}).get("alternate_labels", [])
        if key == "preferred_label":
            current = record.get("localizations", {}).get("eng", {}).get("preferred_label")
        if current == expected:
            continue
        # When a newer record change touched this field, its before value
        # must show the earlier verified after state. For additive witness
        # changes the older group/reference lists must remain a subset.
        later = [
            z.get("replaced_field_values", {})
            for z in all_receipts[index + 1:]
            if key in z.get("before", {})
        ]
        check(bool(later), f"{source_id}: receipt field {key} silently diverged")
        first = later[0]["before"][key]
        check(first == expected,
              f"{source_id}: later receipt does not begin at previous after state")
        if isinstance(current, list) and isinstance(expected, list):
            check(all(v in current for v in expected),
                  f"{source_id}: previously corrected values later lost")


def validate(data: Path, ledger_path: Path, pinned: dict[str, Path] | None = None) -> dict:
    register = load_json(ledger_path)
    lock = load_json(data / "source.lock.json")
    check(register.get("schema_version") == 1, "Unrecognized resolution ledger")
    check(register.get("pin") == {
        "wlc": lock["source_editions"]["wlc"]["edition"],
        "sblgnt": lock["source_editions"]["sblgnt"]["edition"],
    }, "Resolution proof editions do not match data/source.lock.json")
    cases = register.get("cases")
    check(isinstance(cases, list) and bool(cases), "No resolution cases")
    seen = set()
    counters: Counter[str] = Counter()
    wanted_words: dict[str, set[str]] = {"wlc": set(), "sblgnt": set()}
    old = load_json(data / "source-key-identity-review-115.json")
    prior = {x["source_id"]: x for x in old["reviews"]}

    for item in cases:
        source_id = item.get("source_id")
        check(isinstance(source_id, str) and source_id.count(":") == 1
              and source_id not in seen, f"Duplicate/invalid resolved identity {source_id!r}")
        seen.add(source_id)
        kind, name = source_id.split(":", 1)
        check(kind in KIND_DIR and name and "/" not in name and ".." not in name,
              f"Unsafe case source ID {source_id}")
        p = data / "entities" / KIND_DIR[kind] / (name + ".json")
        check(p.is_file(), f"Resolved record absent: {source_id}")
        entity = load_json(p)
        check(entity["id"] == source_id and entity["bsi"]["source_id"] == source_id,
              f"{source_id}: provenance identity mismatch")
        check(re.fullmatch(r"[0-9a-f]{64}", entity["bsi"]["source_sha256"]) is not None,
              f"{source_id}: no immutable original fingerprint")
        outcome = item.get("outcome")
        check(outcome in {"corrected", "verified_correct"},
              f"{source_id}: classified is NOT a resolution")
        counters[outcome] += 1
        claim = item.get("claim")
        check(isinstance(claim, str) and len(claim) >= 70,
              f"{source_id}: no substantial source-specific conclusion")
        check(item.get("proof_kind") in {
            "reversible_edit", "pinned_existing_indirect", "derived_allotment",
            "contextual_comparison",
        }, f"{source_id}: unsupported form of resolution proof")
        ids = item.get("evidence_word_ids")
        check(isinstance(ids, list) and len(ids) > 0 and len(ids) == len(set(ids)),
              f"{source_id}: missing/repeated exact original-word proof")
        for wid in ids:
            check(isinstance(wid, str)
                  and any(pattern.fullmatch(wid) for pattern in PINNED_ID.values()),
                  f"{source_id}: invalid original-word ID {wid!r}")
            corpus = "wlc" if wid[0] == "o" else "sblgnt"
            book=int(wid[1:3])
            check(1 <= book <= 39 if corpus == "wlc" else 40 <= book <= 66,
                  f"{source_id}: source word outside pinned biblical book canon: {wid}")
            wanted_words[corpus].add(wid)
        targets = item.get("target_key_verses")
        check(isinstance(targets, list) and len(targets) == len(set(targets))
              and all(isinstance(v, str) and BCV8.fullmatch(v) for v in targets),
              f"{source_id}: missing or malformed target key")
        check(set(targets).issubset(source_history(entity)),
              f"{source_id}: resolved verse absent from source and documented history")
        origin = item.get("review_origin")
        check(origin in {"data/source-key-identity-review-115.json",
                         "PR_139_independent_source_corroboration"},
              f"{source_id}: unsupported review origin")
        if origin == "data/source-key-identity-review-115.json":
            oldcase = prior.get(source_id)
            check(oldcase is not None
                  and oldcase["classification"] not in {
                      "uncertain_not_promoted", "geographical_inference_not_direct"}
                  and oldcase["rationale"] in claim,
                  f"{source_id}: unresolved review relabeled as correct")
            check((oldcase["editorial_outcome"] ==
                   "source_record_corrected_in_this_review") == (outcome == "corrected"),
                  f"{source_id}: changed/no-change status differs from editorial source")
        if outcome == "corrected":
            check(item["proof_kind"] == "reversible_edit"
                  and isinstance(item.get("required_action"), str),
                  f"{source_id}: correction needs explicit action receipt")
            require_real_receipt(entity, item["required_action"], source_id)
        else:
            check("required_action" not in item,
                  f"{source_id}: no-change case pretends to have an edit")
            proof_kind = item["proof_kind"]
            if proof_kind == "pinned_existing_indirect":
                case = prior[source_id]
                linked = {
                    w for link in case.get("existing_indirect_word_links", [])
                    for w in (link["word_id"],)
                }
                check(linked.issubset(set(ids)) and linked,
                      f"{source_id}: no existing exact coreference cited")
                check(all(any(w in g for f in ("subject_referents", "pronominal_referents")
                              for groups in entity.get(f, {}).values() for g in groups)
                          for w in linked),
                      f"{source_id}: indirect word does not exist in native data")
            elif proof_kind == "derived_allotment":
                verse = item.get("proof_territory_allotment")
                check(kind == "place" and entity.get("added_entry") is True
                      and "place:Israel" in entity.get("subregion_of", [])
                      and not entity["references"] and not entity["key_references"]
                      and not entity["explicit_instances"] and not targets
                      and BCV8.fullmatch(verse or "") is not None
                      and any(w[1:9] == verse for w in ids),
                      f"{source_id}: fabricated word/key on source-derived territory")
            else:
                check(proof_kind == "contextual_comparison" and bool(targets),
                      f"{source_id}: no source-anchored context for correct verdict")
                check(all(v not in {
                    w[1:9] for groups in entity["explicit_instances"].values()
                    for group in groups for w in group
                } for v in targets),
                      f"{source_id}: direct original source words need their own audit")
                # Context can be the same verse, an adjacent pericope or an
                # explicitly identified elsewhere; never pretend it is a
                # direct name in the target verse without lexical evidence.
                check("not a direct" in claim.lower() or
                      "not an" in claim.lower() or "without" in claim.lower()
                      or "context" in claim.lower() or "genealog" in claim.lower()
                      or "source" in claim.lower(),
                      f"{source_id}: direct/contextual distinction undocumented")

    if pinned is not None:
        check(set(pinned) == {"wlc", "sblgnt"}, "Both pinned editions are required")
        for corpus, path in pinned.items():
            found = set()
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                check("xml:id" in (reader.fieldnames or []),
                      f"No pinned source ID column in {path}")
                for row in reader:
                    wid = row["xml:id"]
                    if wid in wanted_words[corpus]:
                        check(wid not in found, f"Duplicate original word {wid}")
                        found.add(wid)
            check(found == wanted_words[corpus],
                  f"Missing locked original words in {corpus}: "
                  f"{sorted(wanted_words[corpus] - found)}")
    return {
        "distinct_resolved": len(seen),
        "corrected": counters["corrected"],
        "verified_correct": counters["verified_correct"],
        "pinned_original_words": sum(map(len, wanted_words.values())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--wlc", type=Path)
    parser.add_argument("--sblgnt", type=Path)
    args = parser.parse_args()
    if (args.wlc is None) != (args.sblgnt is None):
        parser.error("Both original editions are required for source word verification")
    pins = (None if args.wlc is None
            else {"wlc": args.wlc, "sblgnt": args.sblgnt})
    print("BRSi_RESOLVED_SOURCE_KEYS " + json.dumps(
        validate(args.data, args.ledger, pins), sort_keys=True))


if __name__ == "__main__":
    main()
