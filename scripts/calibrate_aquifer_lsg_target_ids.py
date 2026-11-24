#!/usr/bin/env python3
"""Independently calibrate Aquifer target selectors against attested NT words.

The original Clear.Bible token-to-LSG 1.0.2 word mapping was generated from
its actual French target TSV and source OSIS. Compare that authoritative,
source-locked word mapping against the auxiliary Aquifer target and MACULA
witnesses. Never assume numeric selectors identify the same word.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path


def load_gzip_json(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def calibrate(gold: dict, reconciled: dict) -> dict:
    if gold.get("format") != "brsi-curated-translation-word-index-candidate":
        raise ValueError("not the original text-proven NT word index")
    if reconciled.get("format") != "brsi-original-and-independent-word-corroboration-candidate":
        raise ValueError("not the BRSI MACULA-word witness index")
    if gold["curated_osis_sha256"] != reconciled["curated_osis_sha256"]:
        raise ValueError("exact authored LSG edition mismatch")
    if gold["source_alignment_revision"] != reconciled["source_clear_bible_revision"]:
        raise ValueError("original Clear.Bible revision mismatch")
    if len(gold["rows"]) != reconciled["original_group_counts"]["nt"]:
        raise ValueError("NT original alignment source group count changed")
    counts = Counter()
    examples = []
    for ordinal, prior in enumerate(gold["rows"]):
        current = reconciled["rows"][ordinal]
        if (current["canon"] != "nt" or
            current["original_ordinal"] != prior["original_ordinal"] or
            current["original_macula_ids"] != prior["original_macula_ids"] or
            current["original_clear_bible_target_ids"] != prior["original_target_ids"]):
            raise ValueError("unaligned NT original word record identities")
        if prior["status"] != "surface_word_position_candidate":
            counts["original_nt_word_mapping_unresolved"] += 1
            continue
        counts["original_nt_exact_french_word_candidates"] += 1
        attested = prior["curated_bcv"] + ":" + str(prior["curated_diagnostic_word_ordinal"])
        targets = current["original_target_word_witness_ids"]
        sources = current["aquifer_source_word_witness_ids"]
        if attested in targets:
            counts["aquifer_same_original_target_id_exact_word"] += 1
        elif targets:
            counts["aquifer_same_original_target_id_wrong_word"] += 1
            if len(examples) < 12:
                examples.append({"original_target_id": prior["original_target_ids"][0],
                                 "expected_bcv_word": attested,
                                 "actual_candidate_words": targets[:4],
                                 "evidence": "different_target_position"})
        else:
            counts["aquifer_original_target_id_not_located"] += 1
        if attested in sources:
            counts["aquifer_original_macula_id_same_word"] += 1
        elif sources:
            counts["aquifer_original_macula_id_other_word"] += 1
        else:
            counts["aquifer_original_macula_id_unmapped"] += 1
    expected = gold["coverage"]["surface_word_position_candidate"]
    if counts["original_nt_exact_french_word_candidates"] != expected:
        raise ValueError("original NT word candidate census changed")
    if (counts["aquifer_same_original_target_id_exact_word"] +
        counts["aquifer_same_original_target_id_wrong_word"] +
        counts["aquifer_original_target_id_not_located"] != expected):
        raise ValueError("Aquifer target NT calibration is incomplete")
    return {
        "format": "brsi-original-target-id-word-calibration",
        "status": "private_nonpublishing_diagnostic",
        "curated_osis_sha256": gold["curated_osis_sha256"],
        "original_revision": gold["source_alignment_revision"],
        "aquifer_revision": reconciled["source_aquifer_revision"],
        "counts": dict(sorted(counts.items())),
        "examples": examples,
        "original_scripture_changed": False,
        "target_id_equivalence_assumed": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold-nt-index", type=Path, required=True)
    p.add_argument("--auxiliary-index", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    report = calibrate(load_gzip_json(a.gold_nt_index),
                       load_gzip_json(a.auxiliary_index))
    a.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
