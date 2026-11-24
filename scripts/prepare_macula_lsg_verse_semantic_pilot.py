#!/usr/bin/env python3
"""Prepare PRIVATE whole-verse MACULA–LSG semantic tasks; validate model proposals.

A verse, its clause-level interpretation and its complete original/authorial
context are the units of reasoning. No lemma-position inference occurs here.
This tool DOES NOT perform bilingual reasoning or certify any translation:
a separate model/reviewer supplies its explicit structured proposals.
All Scripture-bearing output stays local and private; public receipts are
aggregate, source-text-free, and explicitly nonpublishing.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = "brsi-whole-verse-semantic-training-pilot-v1"
DECISIONS = {"phrase_span", "grammatical_unpaired", "undetermined"}
GRAMMAR = {"agreement", "case", "article", "aspect", "tense",
           "particle", "clitic", "discourse", "other"}
UNCERTAINTY = {"versification", "missing_target", "conflicting_sources",
               "unclear_syntax", "no_independent_evidence", "other"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def pack_private(obj: dict) -> bytes:
    data = io.BytesIO()
    with gzip.GzipFile(fileobj=data, mode="wb", filename="",
                       mtime=0, compresslevel=9) as output:
        output.write(canonical_bytes(obj))
    return data.getvalue()


def load_pinned_dossier(path: Path, lock: dict) -> tuple[dict, str]:
    packed = path.read_bytes()
    digest = sha256(packed)
    if digest != lock["private_dossiers_gzip_sha256"]:
        raise ValueError("private original/LSG dossier differs from frozen source digest")
    dossier = json.loads(gzip.decompress(packed))
    if (dossier["kind"] != "brsi-private-exact-source-semantic-human-review-dossiers"
            or dossier["schema_version"] != 1
            or dossier["reviewed_case_count"] != 0
            or dossier["semantic_links_automatically_approved"] != 0
            or dossier["model_proposals_included"]
            or dossier["publication_authorized"]
            or dossier["source_index_gzip_sha256"] != lock["source_index_gzip_sha256"]
            or dossier["authored_french_osis_sha256"] !=
            lock["authored_french_osis_sha256"]):
        raise ValueError("dossier provenance, independent gold or edition boundary changed")
    return dossier, digest


def _full_original_tokens(dossier: dict, verse: str) -> list[dict]:
    tokens = dossier["original_source_verses"][verse]
    ids = [word["original_macula_id"] for word in tokens]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("missing or repeated MACULA original tokens")
    if any(word_id[1:9] != verse for word_id in ids):
        raise ValueError("original MACULA tokens cross verse boundary")
    return tokens


def prepare_pilot(dossier: dict, *, dossier_sha: str,
                  nt_count: int = 100, ot_count: int = 100) -> tuple[dict, dict]:
    """Select only TRAINING verses; calibration and blind remain untouched."""
    if nt_count < 1 or ot_count < 1:
        raise ValueError("both Testaments need nonzero verse samples")
    if dossier.get("reviewed_case_count") != 0 or dossier.get(
            "model_proposals_included") is not False:
        raise ValueError("independent review/gold input contaminated by model proposals")
    cases = dossier["cases"]
    if len(cases) != 2000 or len({c["case_id"] for c in cases}) != 2000:
        raise ValueError("frozen 2,000 source-ID sample changed")
    by_verse = defaultdict(list)
    for case in cases:
        verse = case["source_verse_coordinate"]
        if case["context_key"] != verse or verse not in dossier[
                "original_source_verses"]:
            raise ValueError("frozen source verse identity changed")
        if case["evaluation_partition"] != "training":
            continue
        if case["original_target_verse_disagreement"]:
            # Never guess a target verse for an original source conflict.
            continue
        french = dossier["exact_authored_french_verses"][verse]
        if not french["authorial_verse_present"]:
            continue
        by_verse[verse].append(case)
    # Do not expose adjacent French verses belonging to calibration/blind
    # clusters inside training prompts, even when the dossier has them.
    heldout_verses = {c["source_verse_coordinate"] for c in cases
                      if c["evaluation_partition"] != "training"}
    chosen = []
    sizes = {"nt": nt_count, "ot": ot_count}
    for canon in ("nt", "ot"):
        matches = [verse for verse, source_cases in by_verse.items()
                   if all(c["canon"] == canon for c in source_cases)]
        matches.sort(key=lambda v: sha256((SEED + ":" + v).encode()))
        if len(matches) < sizes[canon]:
            raise ValueError("not enough independent training verses for " + canon)
        chosen.extend(matches[:sizes[canon]])
    pilot_id = sha256(canonical_bytes({
        "seed": SEED, "dossier_sha256": dossier_sha,
        "source_index_gzip_sha256": dossier["source_index_gzip_sha256"],
        "authored_french_osis_sha256": dossier["authored_french_osis_sha256"],
        "verses": sorted(chosen),
    }))
    tasks = []
    causes = Counter()
    canon_counts = Counter()
    for verse in sorted(chosen):
        authored = dossier["exact_authored_french_verses"][verse]
        context = dict(authored)
        context["context_neighbors"] = {
            key: neighbor for key, neighbor in authored["context_neighbors"].items()
            if neighbor["verse"] not in heldout_verses
        }
        tokens = _full_original_tokens(dossier, verse)
        ids = {t["original_macula_id"] for t in tokens}
        french_words = context["exact_words"]
        if not french_words or any(w["word_id"] !=
                f"{verse}:{i}" for i, w in enumerate(french_words, 1)):
            raise ValueError("authored French verse word coordinates are not exact")
        if any(case["original_macula_id"] not in ids for case in by_verse[verse]):
            raise ValueError("sampled MACULA original token absent from full verse")
        if context["source_coordinate"] != verse:
            raise ValueError("target verse coordinate does not match original witness")
        for case in by_verse[verse]:
            causes[case["source_cause"]] += 1
        canon = by_verse[verse][0]["canon"]
        canon_counts[canon] += 1
        tasks.append({
            "task_id": sha256((pilot_id + ":" + verse).encode()),
            "canon": canon,
            "original_verse": verse,
            "authored_french_verse": verse,
            "original_tokens_in_source_order": tokens,
            "authored_french": context,
            # Do not reveal Aquifer stratum labels or upstream lexical guesses
            # to the model; they could bias an independent semantic reading.
            "priority_original_macula_ids": [
                case["original_macula_id"]
                for case in sorted(by_verse[verse], key=lambda c: c["case_id"])
            ],
            "original_syntax_constituents_supplied": False,
            "original_source_verse_neighbors_supplied": False,
            "existing_translation_anchors_semantically_approved": False,
            "task_requires_complete_verse_and_clause_reasoning": True,
        })
    pilot = {
        "kind": "brsi-private-whole-verse-semantic-pilot",
        "schema_version": 1,
        "pilot_id": pilot_id,
        "source_dossier_gzip_sha256": dossier_sha,
        "source_index_gzip_sha256": dossier["source_index_gzip_sha256"],
        "authored_french_osis_sha256": dossier["authored_french_osis_sha256"],
        "selection_partition": "training",
        "reasoning_unit": "whole_original_and_french_verse_then_clauses",
        "human_gold_supplied_to_model": False,
        "model_proposals_included": False,
        "original_syntax_constituents_claimed": False,
        "automatic_approved_links": 0,
        "publication_authorized": False,
        "tasks": tasks,
    }
    report = {
        "kind": "brsi-whole-verse-semantic-pilot-source-free-receipt",
        "schema_version": 1,
        "pilot_id": pilot_id,
        "source_dossier_gzip_sha256": dossier_sha,
        "source_index_gzip_sha256": dossier["source_index_gzip_sha256"],
        "authored_french_osis_sha256": dossier["authored_french_osis_sha256"],
        "selection_partition": "training",
        "verses": len(tasks),
        "verses_by_canon": dict(sorted(canon_counts.items())),
        "sampled_unresolved_original_ids": sum(len(t[
            "priority_original_macula_ids"]) for t in tasks),
        "sampled_case_causes": dict(sorted(causes.items())),
        "full_verse_original_tokens": sum(len(t[
            "original_tokens_in_source_order"]) for t in tasks),
        "full_verse_french_words": sum(len(t[
            "authored_french"]["exact_words"]) for t in tasks),
        "model_proposals": 0,
        "human_gold_reviewed": 0,
        "automatically_approved_links": 0,
        "publication_authorized": False,
        "source_text_in_public_receipt": False,
    }
    return pilot, report


def _ordered_consecutive(ids: list[str], all_ids: list[str], label: str) -> None:
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise ValueError(label + " must be nonempty distinct IDs")
    positions = {word: i for i, word in enumerate(all_ids)}
    if any(word not in positions for word in ids):
        raise ValueError(label + " references unattested or cross-verse ID")
    start = positions[ids[0]]
    if ids != all_ids[start:start + len(ids)]:
        raise ValueError(label + " must follow an exact contiguous authored/source span")


def _spans(raw: list, words: list[str], label: str) -> list[dict]:
    if not isinstance(raw, list):
        raise ValueError(label + " must be an explicit span list")
    seen = set()
    for span in raw:
        if not isinstance(span, dict) or set(span) != {"word_ids"}:
            raise ValueError(label + " must have exact word_ids only")
        ids = span["word_ids"]
        _ordered_consecutive(ids, words, label)
        if not seen.isdisjoint(ids):
            raise ValueError(label + " repeats French words across spans")
        seen.update(ids)
    return raw


def _rationale(value, label: str) -> str:
    if not isinstance(value, str) or len(value.strip()) < 20:
        raise ValueError(label + " requires a substantive verse-context rationale")
    return value.strip()


def validate_proposals(pilot: dict, response: dict) -> dict:
    """Structural/provenance validation ONLY; cannot certify actual semantics."""
    if (response.get("schema_version") != 1 or
            response.get("pilot_id") != pilot["pilot_id"] or
            response.get("review_status") != "machine_candidate_only" or
            response.get("automatic_approved_links") != 0 or
            response.get("publication_authorized") is not False or
            set(response) != {"schema_version", "pilot_id", "review_status",
                              "automatic_approved_links", "publication_authorized",
                              "results"}):
        raise ValueError("model result is not from exact pilot or claims approval")
    results = response["results"]
    if not isinstance(results, list):
        raise ValueError("model result must list complete original verse responses")
    expected = {t["task_id"]: t for t in pilot["tasks"]}
    if len(expected) != len(pilot["tasks"]) or len(results) != len(expected):
        raise ValueError("one proposal required per exact source verse")
    seen_tasks = set()
    decisions = Counter()
    covered_words = set()
    original_parts = 0
    for result in results:
        if not isinstance(result, dict) or set(result) != {
                "task_id", "original_verse", "source_verse_sense",
                "french_verse_sense", "clauses"}:
            raise ValueError("verse response must give complete contextual analysis")
        task_id = result["task_id"]
        if task_id not in expected or task_id in seen_tasks:
            raise ValueError("duplicated or unknown original verse task")
        seen_tasks.add(task_id)
        task = expected[task_id]
        verse = task["original_verse"]
        if result["original_verse"] != verse:
            raise ValueError("source verse identity differs from task")
        _rationale(result["source_verse_sense"], "original-language verse sense")
        _rationale(result["french_verse_sense"], "authored French verse sense")
        originals = [row["original_macula_id"] for row in task[
            "original_tokens_in_source_order"]]
        french = [w["word_id"] for w in task["authored_french"]["exact_words"]]
        if not isinstance(result["clauses"], list) or not result["clauses"]:
            raise ValueError("whole verse must be analyzed in clauses")
        clause_originals = []
        for clause in result["clauses"]:
            if not isinstance(clause, dict) or set(clause) != {
                    "original_macula_ids", "french_spans", "clause_sense",
                    "alignments"}:
                raise ValueError("clause lacks exact source/target contextual fields")
            source_ids = clause["original_macula_ids"]
            _ordered_consecutive(source_ids, originals, "original clause")
            clause_originals.extend(source_ids)
            clause_words = _spans(clause["french_spans"], french, "French clause")
            clause_target = {w for span in clause_words for w in span["word_ids"]}
            _rationale(clause["clause_sense"], "source and target clause meaning")
            alignments = clause["alignments"]
            if not isinstance(alignments, list) or not alignments:
                raise ValueError("clause must give original-to-French semantic decisions")
            covered_source = []
            for align in alignments:
                if not isinstance(align, dict) or set(align) != {
                        "original_macula_ids", "french_spans", "decision",
                        "contextual_reason", "grammatical_function",
                        "uncertainty_reason"}:
                    raise ValueError("semantic alignment has missing/unsafe fields")
                source_group = align["original_macula_ids"]
                _ordered_consecutive(source_group, source_ids, "original semantic group")
                covered_source.extend(source_group)
                spans = _spans(align["french_spans"], french, "French semantic span")
                targets = {w for span in spans for w in span["word_ids"]}
                if not targets.issubset(clause_target):
                    raise ValueError("semantic French span lies outside its clause")
                decision = align["decision"]
                if decision not in DECISIONS:
                    raise ValueError("unknown semantic disposition")
                _rationale(align["contextual_reason"], "contextual semantic explanation")
                if decision == "phrase_span":
                    if not spans or align["grammatical_function"] is not None or (
                            align["uncertainty_reason"] is not None):
                        raise ValueError("phrase span cannot claim unrelated disposition")
                elif decision == "grammatical_unpaired":
                    if spans or align["grammatical_function"] not in GRAMMAR or (
                            align["uncertainty_reason"] is not None):
                        raise ValueError("unpaired grammatical function was forced onto French words")
                else:
                    if spans or align["grammatical_function"] is not None or (
                            align["uncertainty_reason"] not in UNCERTAINTY):
                        raise ValueError("uncertain original group cannot claim French equivalence")
                decisions[decision] += len(source_group)
                original_parts += len(source_group)
                covered_words.update(targets)
            if covered_source != source_ids:
                raise ValueError("semantic decisions must cover every original clause token once")
        if clause_originals != originals:
            raise ValueError("clauses must cover the complete original verse exactly once")
    return {
        "kind": "brsi-whole-verse-machine-proposals-source-free-receipt",
        "schema_version": 1,
        "pilot_id": pilot["pilot_id"],
        "source_dossier_gzip_sha256": pilot["source_dossier_gzip_sha256"],
        "analyzed_complete_verses": len(results),
        "original_source_parts_with_machine_disposition": original_parts,
        "machine_dispositions_by_original_part": dict(sorted(decisions.items())),
        "distinct_french_words_used_in_machine_spans": len(covered_words),
        "independently_verified_semantic_links": 0,
        "human_gold_cases_reviewed": 0,
        "automatic_approved_links": 0,
        "publication_authorized": False,
        "source_text_in_public_receipt": False,
    }


def require_outside_repo(path: Path) -> None:
    if path.resolve().is_relative_to(ROOT):
        raise ValueError("private source text and machine candidate data cannot enter Git")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("prepare", "validate"), required=True)
    p.add_argument("--private-dossiers", type=Path)
    p.add_argument("--dossier-lock", type=Path)
    p.add_argument("--nt-verses", type=int, default=100)
    p.add_argument("--ot-verses", type=int, default=100)
    p.add_argument("--private-pilot", type=Path, required=True)
    p.add_argument("--machine-response", type=Path)
    p.add_argument("--pilot-receipt", type=Path)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    require_outside_repo(a.private_pilot)
    require_outside_repo(a.report)
    if a.private_pilot.resolve() == a.report.resolve():
        raise ValueError("private output and aggregate receipt must differ")
    if a.mode == "prepare":
        if not a.private_dossiers or not a.dossier_lock or a.machine_response or a.pilot_receipt:
            raise ValueError("prepare requires pinned private dossiers and lock only")
        require_outside_repo(a.private_dossiers)
        lock = json.loads(a.dossier_lock.read_text(encoding="utf-8"))
        dossier, digest = load_pinned_dossier(a.private_dossiers, lock)
        pilot, receipt = prepare_pilot(dossier, dossier_sha=digest,
                                       nt_count=a.nt_verses, ot_count=a.ot_verses)
        packed = pack_private(pilot)
        a.private_pilot.write_bytes(packed)
        receipt["private_pilot_gzip_sha256"] = sha256(packed)
        receipt["private_pilot_gzip_bytes"] = len(packed)
    else:
        if (not a.machine_response or not a.pilot_receipt or
                a.private_dossiers or a.dossier_lock):
            raise ValueError("validate requires private pilot, exact receipt and model response")
        require_outside_repo(a.machine_response)
        if a.report.resolve() == a.pilot_receipt.resolve():
            raise ValueError("cannot replace the source-locked pilot receipt")
        packed = a.private_pilot.read_bytes()
        locked_receipt = json.loads(a.pilot_receipt.read_text(encoding="utf-8"))
        if (locked_receipt.get("kind") !=
                "brsi-whole-verse-semantic-pilot-source-free-receipt" or
                locked_receipt.get("private_pilot_gzip_sha256") != sha256(packed) or
                locked_receipt.get("private_pilot_gzip_bytes") != len(packed)):
            raise ValueError("private pilot changed since source-locked preparation")
        pilot = json.loads(gzip.decompress(packed))
        if (pilot.get("pilot_id") != locked_receipt.get("pilot_id") or
                pilot.get("source_dossier_gzip_sha256") !=
                locked_receipt.get("source_dossier_gzip_sha256")):
            raise ValueError("private pilot provenance differs from source-free receipt")
        if pilot.get("kind") != "brsi-private-whole-verse-semantic-pilot":
            raise ValueError("incorrect original verse-pilot input")
        response = json.loads(a.machine_response.read_text(encoding="utf-8"))
        receipt = validate_proposals(pilot, response)
        receipt["private_pilot_gzip_sha256"] = sha256(packed)
        receipt["private_machine_response_sha256"] = sha256(
            a.machine_response.read_bytes())
    a.report.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print("BRSI_WHOLE_VERSE_SEMANTIC_SOURCE_FREE", json.dumps({
        "pilot_id": receipt["pilot_id"],
        "verses": receipt.get("verses", receipt.get("analyzed_complete_verses")),
        "automatic_approved_links": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
