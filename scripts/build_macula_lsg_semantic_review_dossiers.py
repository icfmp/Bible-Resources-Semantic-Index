#!/usr/bin/env python3
"""Build *private* MACULA–authored-LSG review dossiers; never create gold labels.

The frozen 2,000-case source-ID sample is converted into exact original-word
and authored French verse context, without showing any machine-proposed
translation. Original sources and edition are checked byte-for-byte.
Output is a private deterministic gzip plus a source-text-free JSON receipt.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "brsi_phrase_for_review", ROOT / "scripts" /
    "audit_macula_lsg_phrase_brackets.py")
phrase = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(phrase)
sampler = phrase.sampler
lexical = phrase.lexical
bridge = phrase.bridge

SPLIT_SEED = "brsi-semantic-review-verse-cluster-split-v1"
FORM_FIELDS = ("text", "surface", "word", "unicode", "form")
MORPH_FIELDS = ("morph", "morphology", "morph_code")
POS_FIELDS = ("sp", "pos", "partOfSpeech", "part_of_speech")
SOURCE_PIN_COUNT = {"nt": 137741, "ot": 469476}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def partition(verse: str) -> str:
    if len(verse) != 8 or not verse.isdecimal():
        raise ValueError("invalid verse used in blind partition")
    value = hashlib.sha256((SPLIT_SEED + ":" + verse).encode()).digest()[0]
    if value < 153:
        return "training"
    if value < 205:
        return "calibration"
    return "blind_validation"


def _first_present(columns: list[str], preferred: tuple[str, ...]) -> str | None:
    return next((col for col in preferred if col in columns), None)


def selected_original_context(path: Path, canon: str, expected_sha: str,
                              verses: set[str]) -> tuple[dict, dict]:
    if lexical.sha256_file(path) != expected_sha:
        raise ValueError("MACULA original source SHA-256 differs from exact pinned input")
    context = defaultdict(list)
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = reader.fieldnames or []
        if not {"xml:id", "lemma"}.issubset(fields):
            raise ValueError("original MACULA source lacks exact token IDs or lemma column")
        form_field = _first_present(fields, FORM_FIELDS)
        morph_field = _first_present(fields, MORPH_FIELDS)
        pos_field = _first_present(fields, POS_FIELDS)
        prefix = "n" if canon == "nt" else "o"
        total = blank_forms = 0
        for record in reader:
            raw_id = (record.get("xml:id") or "").strip()
            source = raw_id if raw_id.startswith(prefix) else prefix + raw_id
            source_canon, _book, verse = sampler.coordinates(source)
            if source_canon != canon or source in seen:
                raise ValueError("MACULA source has duplicate or wrong-testament token ID")
            seen.add(source)
            total += 1
            if verse not in verses:
                continue
            form = (record.get(form_field) or "") if form_field else ""
            if not form:
                blank_forms += 1
            context[verse].append({
                "original_macula_id": source,
                "source_form": form if form else None,
                "lemma": record.get("lemma") or None,
                "morphology": (record.get(morph_field) or None) if morph_field else None,
                "part_of_speech": (record.get(pos_field) or None) if pos_field else None,
            })
    if total != SOURCE_PIN_COUNT[canon]:
        raise ValueError("complete MACULA source census differs from pinned baseline")
    if set(context) != verses:
        raise ValueError("selected original verse lacks MACULA source context")
    return dict(sorted(context.items())), {
        "original_tokens_scanned": total,
        "original_context_verses": len(context),
        "original_context_token_rows": sum(len(v) for v in context.values()),
        "source_form_column": form_field,
        "morphology_column": morph_field,
        "part_of_speech_column": pos_field,
        "selected_context_tokens_without_source_form": blank_forms,
    }


def _neighbor(verse: str, offset: int, authored: dict[str, str]) -> str | None:
    # Strictly within the same canonical book/chapter, with no invented verses.
    number = int(verse[-3:]) + offset
    if number < 1 or number > 176:
        return None
    ref = verse[:-3] + f"{number:03d}"
    return ref if ref in authored else None


def authored_french_context(authored: dict[str, str], verses: set[str]) -> dict:
    result = {}
    for verse in sorted(verses):
        if verse not in authored:
            result[verse] = {"authorial_verse_present": False,
                             "source_coordinate": verse,
                             "exact_words": [], "nfc_verse": None,
                             "context_neighbors": {}}
            continue
        text = bridge.ed.unicodedata.normalize("NFC", authored[verse])
        tokens = bridge.word_tokens(text)
        result[verse] = {
            "authorial_verse_present": True,
            "source_coordinate": verse,
            "nfc_verse": text,
            "nfc_verse_sha256": sha256(text.encode("utf-8")),
            "exact_words": [
                {"word_id": f"{verse}:{i}", "surface": word,
                 "nfc_start_codepoint": left, "nfc_end_codepoint": right}
                for i, (word, left, right) in enumerate(tokens, start=1)],
            "context_neighbors": {
                name: {"verse": ref, "nfc_verse": bridge.ed.unicodedata.normalize(
                    "NFC", authored[ref])}
                for name, offset in (("previous", -1), ("next", 1))
                if (ref := _neighbor(verse, offset, authored)) is not None
            },
        }
    return result


def build_dossiers(index: dict, reviewed_cases: list[dict],
                   original_nt: dict, original_ot: dict,
                   authored: dict[str, str], *, source_pin: dict,
                   sample_sha: str) -> tuple[dict, dict]:
    if len(reviewed_cases) != 2000 or len({
            item["original_macula_id"] for item in reviewed_cases}) != 2000:
        raise ValueError("private source-frozen review case count/identity changed")
    selected_verses = {
        "nt": {x["source_verse_coordinate"] for x in reviewed_cases
               if x["canon"] == "nt"},
        "ot": {x["source_verse_coordinate"] for x in reviewed_cases
               if x["canon"] == "ot"},
    }
    tokens = {"nt": original_nt, "ot": original_ot}
    french = authored_french_context(authored, selected_verses["nt"] |
                                    selected_verses["ot"])
    original_by_verse = {}
    for canon in ("nt", "ot"):
        if set(tokens[canon]) != selected_verses[canon]:
            raise ValueError("selected MACULA context does not match review case verses")
        original_by_verse.update(tokens[canon])
    cases = []
    by_partition = Counter()
    by_partition_canon = defaultdict(Counter)
    by_partition_stratum = defaultdict(Counter)
    mismatch = 0
    unavailable = 0
    original_ids = index["by_original_macula_id"]
    causes = index["unlinked_cause_by_original_macula_id"]
    for item in reviewed_cases:
        source = item["original_macula_id"]
        canon, book, verse = sampler.coordinates(source)
        if (canon != item["canon"] or book != item["book_code"] or
                verse != item["source_verse_coordinate"] or
                causes.get(source) != item["source_cause"] or
                source not in original_ids):
            raise ValueError("sampled case identity or original cause changed")
        if sum(source == row["original_macula_id"]
               for row in original_by_verse[verse]) != 1:
            raise ValueError("source MACULA ID absent/duplicated in selected verse")
        original_targets = {
            target[:8]
            for position in original_ids[source]
            for target in index["rows"][position].get(
                "original_clear_bible_target_ids", [])
        }
        if any(len(target) != 8 or not target.isdecimal()
               for target in original_targets):
            raise ValueError("malformed original target verse coordinate")
        disagreement = any(target != verse for target in original_targets)
        mismatch += int(disagreement)
        no_french = not french[verse]["authorial_verse_present"]
        unavailable += int(no_french)
        split = partition(verse)
        by_partition[split] += 1
        by_partition_canon[split][canon] += 1
        by_partition_stratum[split][item["source_cause"]] += 1
        cases.append({
            "case_id": item["case_id"],
            "original_macula_id": source,
            "source_cause": item["source_cause"],
            "canon": canon,
            "source_verse_coordinate": verse,
            "context_key": verse,
            "evaluation_partition": split,
            "original_clear_bible_target_verse_coordinates":
                sorted(original_targets),
            "original_target_verse_disagreement": disagreement,
            "review_decision": None,
            "machine_candidate_visible_to_reviewers": False,
            "human_reviewed": False,
            "semantic_equivalence_approved": False,
        })
    if len({x["case_id"] for x in cases}) != 2000:
        raise ValueError("reused original review case ID")
    verse_splits = {}
    for case in cases:
        verse = case["source_verse_coordinate"]
        if verse in verse_splits and verse_splits[verse] != case[
                "evaluation_partition"]:
            raise ValueError("source verse leaked across evaluation partitions")
        verse_splits[verse] = case["evaluation_partition"]
    # Full source context is stored once per verse, not redundantly per
    # sampled source token. The *entire* object is private.
    dossier = {
        "kind": "brsi-private-exact-source-semantic-human-review-dossiers",
        "schema_version": 1,
        "source_index_gzip_sha256": source_pin["gzip_sha256"],
        "source_clear_bible_revision": source_pin["source_clear_bible_revision"],
        "source_aquifer_revision": source_pin["source_aquifer_revision"],
        "authored_french_osis_sha256": source_pin["curated_osis_sha256"],
        "frozen_sample_sha256": sample_sha,
        "split_seed": SPLIT_SEED,
        "reviewed_case_count": 0,
        "semantic_links_automatically_approved": 0,
        "publication_authorized": False,
        "model_proposals_included": False,
        "cases": cases,
        "original_source_verses": dict(sorted(original_by_verse.items())),
        "exact_authored_french_verses": french,
    }
    report = {
        "kind": "brsi-source-locked-private-semantic-review-dossiers-receipt",
        "schema_version": 1,
        "source_index_gzip_sha256": source_pin["gzip_sha256"],
        "source_clear_bible_revision": source_pin["source_clear_bible_revision"],
        "source_aquifer_revision": source_pin["source_aquifer_revision"],
        "authored_french_osis_sha256": source_pin["curated_osis_sha256"],
        "frozen_sample_sha256": sample_sha,
        "split_seed": SPLIT_SEED,
        "sample_original_macula_ids": len(cases),
        "original_source_verses": len(verse_splits),
        "original_target_verse_disagreement_cases": mismatch,
        "missing_authored_same_coordinate_verses": unavailable,
        "source_verse_cluster_partition_counts": dict(sorted(by_partition.items())),
        "partition_by_canon": {k: dict(sorted(v.items()))
                               for k, v in sorted(by_partition_canon.items())},
        "partition_by_cause": {k: dict(sorted(v.items()))
                               for k, v in sorted(by_partition_stratum.items())},
        "human_gold_reviewed_cases": 0,
        "model_proposals_shown": 0,
        "automatic_approved_word_links": 0,
        "publication_authorized": False,
        "source_text_in_public_receipt": False,
    }
    return dossier, report


def private_gzip(doc: dict) -> bytes:
    plain = (json.dumps(doc, sort_keys=True, ensure_ascii=False,
                        separators=(",", ":"), allow_nan=False) + "\n").encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", compresslevel=9,
                       mtime=0) as target:
        target.write(plain)
    return buffer.getvalue()


def generate(original_index: Path, correspondence_lock: Path,
             semantic_sample_lock: Path, pivot_lock: Path,
             pivot_nt: Path, pivot_ot: Path,
             curated_lock: Path, curated_root: Path) -> tuple[bytes, dict]:
    lock = json.loads(correspondence_lock.read_text(encoding="utf-8"))
    index, index_sha = phrase.pinned_index(original_index, lock)
    sample_lock = json.loads(semantic_sample_lock.read_text(encoding="utf-8"))
    raw, _ = sampler.render(index, lock, index_sha, per_stratum=500)
    if (sha256(raw) != sample_lock["private_unreviewed_cases_sha256"] or
            sample_lock["source_index_gzip_sha256"] != index_sha or
            sample_lock["case_count"] != 2000):
        raise ValueError("private 2,000-case selection differs from pinned sample")
    cases = json.loads(raw)["cases"]
    verses = {
        c: {case["source_verse_coordinate"] for case in cases
            if case["canon"] == c} for c in ("nt", "ot")}
    pivot = json.loads(pivot_lock.read_text(encoding="utf-8"))["sources"]
    selected = {}
    census = {}
    for c, path in (("nt", pivot_nt), ("ot", pivot_ot)):
        selected[c], census[c] = selected_original_context(
            path, c, pivot[c]["sha256"], verses[c])
    edition = json.loads(curated_lock.read_text(encoding="utf-8"))
    if edition["osis_sha256"] != lock["curated_osis_sha256"]:
        raise ValueError("original published French edition differs from locked source")
    osis = bridge.ed.pinned_file(curated_root, edition["osis_path"],
                                 edition["osis_sha256"])
    authored = bridge.ed.read_osis(osis)
    docket, report = build_dossiers(
        index, cases, selected["nt"], selected["ot"], authored,
        source_pin=lock, sample_sha=sample_lock["private_unreviewed_cases_sha256"])
    report["source_census"] = census
    packed = private_gzip(docket)
    report["private_dossiers_gzip_sha256"] = sha256(packed)
    report["private_dossiers_gzip_bytes"] = len(packed)
    return packed, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("original-index", "correspondence-lock",
                "semantic-sample-lock", "pivot-lock", "pivot-nt",
                "pivot-ot", "curated-lock", "curated-root",
                "private-dossiers", "report"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    for path in (args.private_dossiers, args.report):
        if path.resolve().is_relative_to(ROOT):
            raise ValueError("private review data and reports must not be written into Git")
    if args.private_dossiers.resolve() == args.report.resolve():
        raise ValueError("private review and source-free report outputs must differ")
    packed, report = generate(
        args.original_index, args.correspondence_lock,
        args.semantic_sample_lock, args.pivot_lock, args.pivot_nt,
        args.pivot_ot, args.curated_lock, args.curated_root)
    args.private_dossiers.write_bytes(packed)
    args.report.write_text(json.dumps(report, sort_keys=True,
                                     ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("BRSI_PRIVATE_REVIEW_DOSSIER_RECEIPT",
          json.dumps({"cases": report["sample_original_macula_ids"],
                      "verses": report["original_source_verses"],
                      "split": report["source_verse_cluster_partition_counts"],
                      "gzip_sha256": report["private_dossiers_gzip_sha256"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
