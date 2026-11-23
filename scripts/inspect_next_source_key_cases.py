#!/usr/bin/env python3
"""Read-only original-language examination dossier for queued source identities.

The report is evidence for editorial judgment, not an automatic resolver.
Only pinned Macula WLC/SBLGNT word IDs and native immutable source records
may substantiate a final decision. Never copy or redistribute source texts.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


PATHS = {"person": "people", "place": "places", "group": "groups",
         "deity": "deities", "fauna": "fauna", "flora": "flora", "realia": "realia"}


def verse_neighbors(verse: str) -> set[str]:
    book, chap, no = int(verse[:2]), int(verse[2:5]), int(verse[5:])
    return {f"{book:02d}{chap:03d}{i:03d}" for i in range(max(1, no-2), no+4)}


def index_pinned_verses(paths: dict[str, Path], requested: set[str]) -> dict[str, list[dict]]:
    words = defaultdict(list)
    for corpus, path in paths.items():
        with path.open(encoding="utf-8-sig", newline="") as inp:
            reader=csv.DictReader(inp, delimiter="\t")
            for row in reader:
                wid=row["xml:id"]
                if wid[1:9] not in requested:
                    continue
                words[wid[1:9]].append({
                    "word_id":wid, "english":row["english"], "lemma":row["lemma"],
                    "gloss":row["gloss"], "text":row["text"],
                    "corpus":corpus,
                })
    return words


def summarize(data: Path, candidates: Path, paths: dict[str, Path]) -> list[dict]:
    queue=json.loads(candidates.read_text(encoding="utf-8"))["cases"]
    requested=set()
    for row in queue:
        for verse in row["key_verses"]:
            requested.update(verse_neighbors(verse))
    words=index_pinned_verses(paths, requested)
    reports=[]
    for row in queue:
        source_id=row["source_id"]
        kind,name=source_id.split(":",1)
        record=json.loads((data/"entities"/PATHS[kind]/(name+".json")).read_text(encoding="utf-8"))
        if record["bsi"]["source_id"] != source_id:
            raise ValueError("Identity mismatch: "+source_id)
        explicit=set(w for groups in record["explicit_instances"].values() for g in groups for w in g)
        indirect=set(w for field in ("pronominal_referents","subject_referents")
                     for groups in record[field].values() for g in groups for w in g)
        key_cases=[]
        for verse in row["key_verses"]:
            if verse not in record["key_references"]:
                valid_removals=[
                    c for c in record["bsi"].get("editorial_field_changes",[])
                    if verse in c.get("replaced_field_values",{}).get("before",{}).get("key_references",[])
                    and verse not in c.get("replaced_field_values",{}).get("after",{}).get("key_references",[])
                    and c.get("reason") and c.get("evidence")
                ]
                if not valid_removals:
                    raise ValueError(f"Candidate {source_id}: key {verse} disappeared without a reversible evidenced correction")
            nearby=[]
            for vv in sorted(verse_neighbors(verse)):
                seq=words.get(vv,[])
                selected=[w for w in seq if w["word_id"] in explicit or w["word_id"] in indirect]
                nearby.append({
                    "verse_id":vv,
                    "text":" ".join((w["english"] or w["gloss"] or w["text"]).replace(" ","_")
                                    for w in seq),
                    "word_anchors":[{"id":w["word_id"],"english":w["english"],
                                     "lemma":w["lemma"],"relationship":
                                     "direct" if w["word_id"] in explicit else "indirect"}
                                    for w in selected]
                })
            key_cases.append({"verse":verse,"neighboring_source_verses":nearby})
        reports.append({
            "source_id":source_id,
            "source_sha256":record["bsi"]["source_sha256"],
            "keys":list(record["key_references"]),
            "active_direct_verse_count":len({w[1:9] for w in explicit}),
            "active_indirect_verse_count":len({w[1:9] for w in indirect}),
            "local_english_name":record["localizations"]["eng"]["preferred_label"],
            "nearby":key_cases,
        })
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--candidates",type=Path,required=True)
    parser.add_argument("--wlc",type=Path,required=True)
    parser.add_argument("--sblgnt",type=Path,required=True)
    parser.add_argument("--compact",action="store_true")
    args=parser.parse_args()
    for row in summarize(args.data,args.candidates,{"wlc":args.wlc,"sblgnt":args.sblgnt}):
        if args.compact:
            compact=[]
            for case in row["nearby"]:
                target=case["verse"]
                source=case["neighboring_source_verses"]
                direct=[{"verse":v["verse_id"],"ids":[w["id"] for w in v["word_anchors"]],
                         "words":[w["english"] for w in v["word_anchors"]]}
                        for v in source if v["word_anchors"]]
                text=next((v["text"] for v in source if v["verse_id"]==target),"")
                compact.append({"target":target,"text":text[:230],"nearby_links":direct})
            row={"source_id":row["source_id"],"keys":row["keys"],
                 "direct_verse_count":row["active_direct_verse_count"],
                 "indirect_verse_count":row["active_indirect_verse_count"],
                 "cases":compact}
        print("NEXT_SOURCE_KEY_CASE "+json.dumps(row,ensure_ascii=False,separators=(",",":")))


if __name__=="__main__":
    main()
