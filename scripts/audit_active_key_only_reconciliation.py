#!/usr/bin/env python3
"""Reconcile all active key-only references with *independent* review evidence.

Neither the absence of a general reference nor an English gloss match proves
an original-language word error. This is a live census with explicit
provenance tiers: previously certified, manually qualified place, original
indirect grammar, candidate word requiring identity review, contextual hold.
No source record is altered by this program.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _load_sibling(filename: str, module_name: str):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_word = _load_sibling("audit_all_key_reference_original_words.py", "brsi_key_word_probe")
_source = _load_sibling("audit_source_reference_evidence.py", "brsi_source_reference_probe")
_place = _load_sibling("validate_source_place_attestations.py", "brsi_place_source_validator")
_last = _load_sibling("validate_last_key_only_reviews.py", "brsi_last_key_only_source_validator")
get_macula_words, inventory, review = _word.get_macula_words, _word.inventory, _word.review
audit = _source.audit
validate_places = _place.validate
REGISTERS = (
    "source-key-resolved-115.json",
    "source-key-next-115-resolved.json",
    "source-key-final-128-review.json",
)

def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_existing_reviews(data: Path) -> dict:
    resolved = {}
    for file in REGISTERS:
        ledger = read(data / file)
        for item in ledger["cases"]:
            sid = item["source_id"]
            if sid in resolved:
                raise ValueError("An identity occurs in multiple prior certified source cohorts: " + sid)
            status = item.get("outcome", item.get("decision"))
            if status not in {"corrected", "verified_correct", "secondary_verified"}:
                raise ValueError("Unresolved case falsely counted as a past independent decision: " + sid)
            original = (item.get("original_key_verses") or item.get("target_key_verses")
                        or item.get("key_verses_reviewed"))
            if not isinstance(original, list) or not all(isinstance(v, str) for v in original):
                raise ValueError("Malformed historical source keys: " + sid)
            resolved[sid] = {"keys": set(original), "status": status, "ledger": file}
    if len(resolved) != 358:
        raise ValueError("Original certified history is not exactly 358 nonoverlapping identity decisions")
    return resolved


def reconcile(data: Path, pinned: dict[str, Path] | None = None) -> dict:
    source = audit(data)
    live = inventory(data)
    rows = {(r["source_id"], r["verse_id"]): r for r in live}
    if len(rows) != len(live):
        raise ValueError("Active key-only source pairs were duplicated")
    counted = [
        r for cat, cases in source["cases"].items()
        if cat.startswith("key_outside_general") for r in cases
    ]
    if {(r["source_id"], r["verse_id"]) for r in counted} != set(rows):
        raise ValueError("Source-reference census does not match independent original-word inventory")
    prior = load_existing_reviews(data)
    place_data = read(data / "source-place-attestation-review.json")
    validate_places(data, data / "source-place-attestation-review.json")
    final_audit = _last.validate(data, data / "v1-key-only-final-63-review.json")
    final_pairs = {(c["source_id"], t["verse_id"]): t["decision"]
                   for c in read(data / "v1-key-only-final-63-review.json")["cases"]
                   for t in c["targets"]}
    require_coverage = final_audit["total"] == 63 and len(final_pairs) == 63
    if not require_coverage:
        raise ValueError("Final 63 source decisions do not fully cover frozen key-only pairs")
    place = {c["source_id"]: set(c["original_key_verses"]) for c in place_data["cases"]}
    reviewed_places = set()
    source_words = {} if pinned is None else get_macula_words(
        {r["verse_id"] for r in live}, pinned)
    original_triage = review(live, source_words)
    matched = {
        (r["source_id"], r["verse_id"]): r
        for r in original_triage["cases"]
    }
    if set(rows) != set(matched):
        raise ValueError("Original-language triage skipped a key-only source pair")
    counts = Counter()
    decisions = []
    for sid, verse in sorted(rows):
        item = rows[(sid, verse)]
        prior_entry = prior.get(sid)
        place_entry = sid in place and verse in place[sid]
        src = matched[(sid, verse)]
        # A prior *case-specific* certified decision is stronger than
        # a later whole-source-class guess or candidate English word.
        if prior_entry and verse in prior_entry["keys"]:
            status = "previously_certified"
            provenance = prior_entry["ledger"]
        elif final_pairs.get((sid, verse)) == "verified_contextual":
            status = "newly_independently_certified_context"
            provenance = "v1-key-only-final-63-review.json"
        elif place_entry:
            status = "place_context_individually_qualified"
            provenance = "source-place-attestation-review.json"
            reviewed_places.add(sid)
        elif item["source_indirect_word_claim"]:
            status = "indirect_original_word_requires_coreference"
            provenance = "active_native_indirect_word_link"
        elif pinned is not None and src["status"] == "unlinked_original_word_name_candidate_review":
            status = "lexical_candidate_requires_identity_review"
            provenance = "source_pinned_english_or_gloss_candidate"
        elif int(verse[:2]) > 66:
            status = "out_of_pinned_66_book_scope"
            provenance = "external_corpus_required"
        else:
            status = "contextual_claim_requires_manual_review"
            provenance = "inherited_key_without_corresponding_direct_name"
        if status == "previously_certified" and prior_entry["status"] == "secondary_verified":
            provenance += " (external Greek Maccabees; not Macula)"
        counts[status] += 1
        decisions.append({
            "source_id": sid,
            "verse_id": verse,
            "kind": item["kind"],
            "status": status,
            "provenance": provenance,
            "has_native_indirect_words": item["source_indirect_word_claim"],
            "pinned_candidate_ids": [
                x["word_id"] for x in src["source_word_candidates"]
            ] if pinned is not None else [],
        })
    if sum(counts.values())!=len(decisions):
        raise ValueError("Key-only classification silently lost an indexed source pair")
    # Historical records that have been evidentially corrected no longer appear
    # in the live key-only index: never count them as unresolved or 'missing'.
    for (sid,verse),classification in final_pairs.items():
        if classification=="corrected" and (sid,verse) in rows:
            raise ValueError("Repaired erroneous/now-direct key still appears as unlinked")
    return {
        "schema_version": 1,
        "scope": "read_only_current_native_key_only_source_census",
        "source_records_scanned": source["counts"]["records_scanned"],
        "entities_with_key_only_claims": source["counts"]["records_key_outside_general"],
        "key_only_pairs": len(decisions),
        "original_indirect_pair_count": sum(x["source_indirect_word_claim"] for x in live),
        "previously_certified_unique_source_identities": len(prior),
        "newly_certified_original_pairs_including_native_corrections": final_audit["total"],
        "real_native_corrections_newly_proven": final_audit["corrected_pairs"],
        "unresolved_current_key_only_pairs": sum(
            counts[s] for s in ("indirect_original_word_requires_coreference",
                                "lexical_candidate_requires_identity_review",
                                "contextual_claim_requires_manual_review",
                                "out_of_pinned_66_book_scope")),
        "frozen_original_key_only_pairs": 462,
        "individually_reviewed_unanchored_places": len(place_data["cases"]),
        "counts": dict(sorted(counts.items())),
        "cases": decisions,
        "policy": "A key outside general references is not an error by itself. Candidate spellings, nearby word records and inherited contexts are not final editorial dispositions.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--wlc", type=Path)
    p.add_argument("--sblgnt", type=Path)
    p.add_argument("--report", type=Path)
    p.add_argument("--show-pending", type=int, default=20)
    a = p.parse_args()
    if (a.wlc is None) != (a.sblgnt is None):
        raise ValueError("Both original source editions are required to report lexical candidates")
    pinned = {"wlc": a.wlc, "sblgnt": a.sblgnt} if a.wlc else None
    result = reconcile(a.data, pinned)
    if a.report is not None:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, ensure_ascii=False,
                                      sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("BRSi_KEY_ONLY_RECONCILIATION " + json.dumps({
        k: v for k, v in result.items() if k != "cases"
    }, sort_keys=True))
    for row in [r for r in result["cases"]
                if r["status"] in {"lexical_candidate_requires_identity_review",
                                   "contextual_claim_requires_manual_review"}][:a.show_pending]:
        print("KEY_ONLY_RECONCILIATION_PENDING " + json.dumps(
            row, sort_keys=True))


if __name__ == "__main__":
    main()
