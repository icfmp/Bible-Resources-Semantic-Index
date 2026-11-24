#!/usr/bin/env python3
"""Fail-closed, HUMAN-ONLY MACULA↔curated-LSG phrase-gold adjudication.

Review evidence and any resulting gold remain private. Never turn this
research gold into production translation alignment or Bible highlighting.
A source-locked reviewer dossier is mandatory; no guessed source IDs,
OSIS coordinates or inherited model suggestions are allowed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "brsi_dossiers_for_gold", ROOT / "scripts" /
    "build_macula_lsg_semantic_review_dossiers.py")
dossiers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dossiers)
sampler = dossiers.sampler
phrase = dossiers.phrase

REVIEWER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,63}$")
OUTCOMES = {"phrase_span", "grammatical_unpaired", "undetermined"}
UNPAIRED = {
    "agreement", "case", "article", "aspect", "tense",
    "particle", "clitic", "discourse", "other",
}
UNCERTAIN = {
    "versification", "missing_target", "conflicting_sources",
    "unclear_syntax", "no_independent_evidence", "other",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _strings(value, label: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
            not isinstance(x, str) or not x for x in value):
        raise ValueError(label + " must contain nonempty string IDs")
    if len(value) != len(set(value)):
        raise ValueError(label + " contains duplicate IDs")
    return value


def validated_review(record: dict, case: dict, dossier: dict,
                     *, adjudicator: bool = False) -> dict:
    if not isinstance(record, dict) or record.get("case_id") != case["case_id"]:
        raise ValueError("review case identity does not match frozen sample")
    reviewer = record.get("reviewer_id")
    if not isinstance(reviewer, str) or not REVIEWER.fullmatch(reviewer):
        raise ValueError("invalid independent reviewer identifier")
    if record.get("human_original_checked") is not True or record.get(
            "human_curated_french_checked") is not True:
        raise ValueError("only self-attested human original and authored edition reviews accepted")
    evidence = record.get("evidence")
    if not isinstance(evidence, str) or len(evidence.strip()) < 12:
        raise ValueError("review needs substantive independently checked source evidence")
    if adjudicator and (not isinstance(record.get("adjudication_rationale"), str)
                       or len(record["adjudication_rationale"].strip()) < 12):
        raise ValueError("independent adjudicator must explain disputed review")
    outcome = record.get("decision")
    if outcome not in OUTCOMES:
        raise ValueError("unknown or missing semantic review decision")
    source = case["original_macula_id"]
    verse = case["source_verse_coordinate"]
    original_ids = _strings(record.get("original_macula_ids"),
                            "original MACULA group")
    in_verse = [
        row["original_macula_id"]
        for row in dossier["original_source_verses"][verse]]
    if source not in original_ids:
        raise ValueError("original group does not include the reviewed source")
    positions = []
    for original in original_ids:
        if original not in in_verse:
            raise ValueError("unattested or cross-verse source word")
        positions.append(in_verse.index(original))
    if sorted(positions) != list(range(min(positions), max(positions) + 1)):
        raise ValueError("noncontiguous original source group is not supported")
    if original_ids != [in_verse[i] for i in sorted(positions)]:
        raise ValueError("original source group order changed")
    spans = record.get("french_spans", [])
    if not isinstance(spans, list):
        raise ValueError("French spans must be explicit list")
    normalized_spans = []
    used = set()
    if outcome == "phrase_span":
        if not spans:
            raise ValueError("phrase correspondence has no independently checked French span")
        for span in spans:
            if not isinstance(span, dict) or span.get("verse") != verse:
                # #166 still unresolved; do not guess LSG versification.
                raise ValueError("cross-verse French mapping requires separate edition adjudication")
            french = dossier["exact_authored_french_verses"][verse]
            if not french["authorial_verse_present"]:
                raise ValueError("authored French verse was not available for exact review")
            words = _strings(span.get("word_ids"), "LSG phrase word IDs")
            valid = [token["word_id"] for token in french["exact_words"]]
            positions = []
            for word in words:
                if word not in valid or word in used:
                    raise ValueError("French word not in exact published verse or reused")
                used.add(word)
                positions.append(valid.index(word))
            if positions != list(range(positions[0], positions[0] + len(positions))):
                raise ValueError("French phrase word span is reordered or not contiguous")
            normalized_spans.append({"verse": verse, "word_ids": words})
        if record.get("unpaired_function") is not None or record.get(
                "undetermined_reason") is not None:
            raise ValueError("phrase outcome mixes incompatible grammatical statuses")
    else:
        if spans:
            raise ValueError("unpaired or undetermined review cannot force French highlights")
        if outcome == "grammatical_unpaired":
            if record.get("unpaired_function") not in UNPAIRED or record.get(
                    "undetermined_reason") is not None:
                raise ValueError("explicit grammar outcome requires its reviewed function")
        elif (record.get("undetermined_reason") not in UNCERTAIN
              or record.get("unpaired_function") is not None):
            raise ValueError("undetermined outcome must document why evidence is insufficient")
    return {
        "case_id": case["case_id"],
        "reviewer_id": reviewer,
        "decision": outcome,
        "original_macula_ids": original_ids,
        "french_spans": normalized_spans,
        "unpaired_function": record.get("unpaired_function"),
        "undetermined_reason": record.get("undetermined_reason"),
        "evidence": evidence.strip(),
        "human_original_checked": True,
        "human_curated_french_checked": True,
        **({"adjudication_rationale": record["adjudication_rationale"].strip()}
           if adjudicator else {}),
    }


def _substantive(review: dict) -> str:
    return json.dumps({key: review[key] for key in (
        "decision", "original_macula_ids", "french_spans", "unpaired_function",
        "undetermined_reason")}, sort_keys=True, separators=(",", ":"))


def evaluate(dossier: dict, submissions: dict) -> tuple[dict, dict]:
    if dossier["reviewed_case_count"] or dossier["semantic_links_automatically_approved"]:
        raise ValueError("source dossier unexpectedly contains purported prior gold")
    if dossier["model_proposals_included"] or dossier["publication_authorized"]:
        raise ValueError("source dossier is not independent blind human review evidence")
    if submissions.get("schema_version") != 1 or not isinstance(
            submissions.get("reviews"), list) or not isinstance(
            submissions.get("adjudications"), list):
        raise ValueError("unsupported or malformed submitted human gold JSON")
    cases = {c["case_id"]: c for c in dossier["cases"]}
    if len(cases) != len(dossier["cases"]):
        raise ValueError("source dossier duplicated a frozen review case")
    reviews = defaultdict(list)
    adjudications = {}
    for record in submissions["reviews"]:
        if not isinstance(record, dict) or record.get("case_id") not in cases:
            raise ValueError("non-sampled review case")
        case = cases[record["case_id"]]
        valid = validated_review(record, case, dossier)
        if valid["reviewer_id"] in {r["reviewer_id"] for r in reviews[case["case_id"]]}:
            raise ValueError("duplicate reviewer submission for one case")
        reviews[case["case_id"]].append(valid)
    for record in submissions["adjudications"]:
        if not isinstance(record, dict) or record.get("case_id") not in cases:
            raise ValueError("adjudication references non-sampled case")
        key = record["case_id"]
        if key in adjudications:
            raise ValueError("multiple adjudications for same frozen case")
        adjudications[key] = validated_review(
            record, cases[key], dossier, adjudicator=True)

    gold = []
    counts = Counter()
    by_reason = defaultdict(Counter)
    for key in sorted(cases):
        case = cases[key]
        observed = reviews[key]
        adjudication = adjudications.get(key)
        reviewers = {r["reviewer_id"] for r in observed}
        if len(observed) < 2:
            if adjudication:
                raise ValueError("adjudicator cannot override fewer than two reviews")
            counts["awaiting_independent_dual_review"] += 1
            by_reason[case["source_cause"]]["awaiting_review"] += 1
            continue
        choices = {_substantive(review) for review in observed}
        if len(choices) == 1:
            if adjudication:
                raise ValueError("uncontested review must not introduce adjudicator")
            chosen = observed[0]
            counts["independently_agreed_cases"] += 1
        else:
            counts["disputed_cases"] += 1
            if not adjudication:
                counts["unresolved_disputed_cases"] += 1
                by_reason[case["source_cause"]]["disputed_pending"] += 1
                continue
            if adjudication["reviewer_id"] in reviewers:
                raise ValueError("disagreement needs a distinct third adjudicator")
            chosen = adjudication
            counts["resolved_by_independent_adjudication"] += 1
        counts["research_gold_cases"] += 1
        counts["gold_" + chosen["decision"]] += 1
        by_reason[case["source_cause"]][chosen["decision"]] += 1
        gold.append({
            "case_id": key,
            "original_macula_id": case["original_macula_id"],
            "source_verse_coordinate": case["source_verse_coordinate"],
            "source_cause": case["source_cause"],
            "evaluation_partition": case["evaluation_partition"],
            "gold_research_decision": chosen,
            "independent_source_reviews": observed,
            "adjudication": adjudication,
            "automatic_production_approval": False,
            "publication_authorized": False,
        })
    if counts["research_gold_cases"] + counts["unresolved_disputed_cases"] + counts[
            "awaiting_independent_dual_review"] != len(cases):
        raise ValueError("gold review census inconsistent")
    if gold and any(case["automatic_production_approval"] for case in gold):
        raise ValueError("gold cannot automatically become production alignment")
    private = {
        "kind": "brsi-private-reviewed-semantic-gold-not-distributed",
        "schema_version": 1,
        "source_dossiers_sha256": submissions["source_dossiers_gzip_sha256"],
        "human_gold_cases": len(gold),
        "production_approved": False,
        "publication_authorized": False,
        "adjudicated_cases": gold,
    }
    report = {
        "kind": "brsi-semantic-gold-adjudication-source-free-receipt",
        "schema_version": 1,
        "source_dossiers_gzip_sha256": submissions["source_dossiers_gzip_sha256"],
        "review_case_count": len(cases),
        "total_human_submissions": sum(map(len, reviews.values())),
        "adjudicator_submissions": len(adjudications),
        "counts": dict(sorted(counts.items())),
        "by_unlinked_source_cause": {
            reason: dict(sorted(by_reason[reason].items()))
            for reason in sampler.STRATA},
        "human_gold_cases": len(gold),
        "model_evaluations_performed": 0,
        "automatic_production_approvals": 0,
        "publication_authorized": False,
        "source_text_in_public_receipt": False,
    }
    return private, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("private-dossiers", "dossier-lock", "reviews-json",
                "private-gold", "report"):
        parser.add_argument("--" + arg, required=True, type=Path)
    args = parser.parse_args()
    for path in (args.private_gold, args.report):
        if path.resolve().is_relative_to(ROOT):
            raise ValueError("human gold and reports must not be stored in repository")
    if args.private_gold.resolve() == args.report.resolve():
        raise ValueError("gold data and source-free receipt output must differ")
    expected = json.loads(args.dossier_lock.read_text(encoding="utf-8"))
    blob = args.private_dossiers.read_bytes()
    actual = digest(blob)
    if expected["private_dossiers_gzip_sha256"] != actual:
        raise ValueError("input review dossier gzip differs from exact source-pinned lock")
    dossier = json.loads(gzip.decompress(blob))
    if dossier["frozen_sample_sha256"] != expected["frozen_sample_sha256"]:
        raise ValueError("review dossier sample identity differs from frozen cohort")
    reviews = json.loads(args.reviews_json.read_text(encoding="utf-8"))
    if reviews.get("source_dossiers_gzip_sha256") != actual:
        raise ValueError("human review submission references different source dossier")
    private, report = evaluate(dossier, reviews)
    packed = dossiers.private_gzip(private)
    report["private_gold_gzip_sha256"] = digest(packed)
    report["private_gold_gzip_bytes"] = len(packed)
    args.private_gold.write_bytes(packed)
    args.report.write_text(json.dumps(report, ensure_ascii=False,
                                     sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print("BRSI_SEMANTIC_GOLD_HUMAN_ONLY",
          json.dumps({"research_gold_cases": report["human_gold_cases"],
                      "submitted_reviews": report["total_human_submissions"],
                      "private_gold_sha256": report["private_gold_gzip_sha256"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
