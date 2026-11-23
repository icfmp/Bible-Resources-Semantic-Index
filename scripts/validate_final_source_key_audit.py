#!/usr/bin/env python3
"""Strict offline review of the last frozen 128 source-key identities.

A case is not 'resolved' merely because it was selected or probed.
Original Hebrew and Greek excerpts are re-collated independently from the
exact pinned Macula TSVs in CI. Out-of-corpus Greek Maccabees cases remain a
distinct, non-Macula-verified outcome; unresolved cases never count as done.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PATHS={"deity":"deities","flora":"flora","fauna":"fauna","group":"groups",
       "person":"people","place":"places","realia":"realia"}
STATUS={"corrected","verified_correct","secondary_verified","unresolved"}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def original_history(record):
    hist=set(record["key_references"])
    for receipt in record["bsi"].get("editorial_field_changes",[]):
        before=receipt.get("replaced_field_values",{}).get("before",{})
        hist.update(before.get("key_references",[]))
    return hist

def check_receipt(record, row):
    id=row["source_id"]
    require(record["bsi"]["review_status"]=="editorially_reviewed",
            id+": claimed edit without editorial review")
    receipts=[r for r in record["bsi"].get("editorial_field_changes",[])
              if r.get("action")==row.get("required_receipt_action")]
    require(len(receipts)==1,id+": missing or duplicate final correction receipt")
    receipt=receipts[0]
    require(len(receipt.get("reason",""))>=65 and bool(receipt.get("evidence")),
            id+": insufficient independent correction rationale")
    change=receipt.get("replaced_field_values",{})
    before,after=change.get("before"),change.get("after")
    require(isinstance(before,dict) and isinstance(after,dict)
            and before!=after and set(before)==set(after) and bool(after),
            id+": irreversible or no-op correction")
    for field, value in after.items():
        actual=(record.get("localizations",{}).get("eng",{}).get(field)
                if field in {"preferred_label","alternate_labels"}
                else record.get(field))
        require(actual==value,id+": corrected field "+field+" has drifted")
    keys=row["original_key_verses"]
    require(any(k in set(before.get("key_references",[])) or k in record["key_references"]
                for k in keys),id+": edit unrelated to frozen source keys")
    if row["required_receipt_action"]=="adjudicate_final_source_key_mismatch":
        require("key_references" in before and
                (set(before["key_references"])!=set(after["key_references"]) or
                 "alternate_labels" in before),
                id+": no changed key claim in final receipt")

def validate(data:Path, ledger_path:Path,
             wlc:Path|None=None, sblgnt:Path|None=None):
    ledger=load(ledger_path)
    select=load(data/ledger["frozen_selection"])
    pool=load(data/ledger["frozen_pool"])
    a=load(data/ledger["previous_resolved"][0])
    b=load(data/ledger["previous_resolved"][1])
    lock=load(data/"source.lock.json")
    require(ledger.get("schema_version")==1,"Wrong review ledger version")
    require(ledger["source_editions"]=={
      "wlc":lock["source_editions"]["wlc"]["edition"],
      "sblgnt":lock["source_editions"]["sblgnt"]["edition"]},
      "Original source editions were silently replaced")
    require(len(a["cases"])==115 and len(b["cases"])==115,
            "Historical prior 230 source decisions not intact")
    already=[x["source_id"] for x in a["cases"]+b["cases"]]
    require(len(set(already))==230,"Prior case cohorts overlap")
    selected={x["source_id"]:x["key_verses"] for x in select["cases"]}
    pooled={x["source_id"] for x in pool["cases"]}
    require(len(selected)==128 and len(pooled)==243,"Frozen queue sizes drifted")
    require(set(selected).issubset(pooled) and not set(selected)&set(already),
            "Overlap with already adjudicated cases")
    require(len(pool["cases"])==len(set(pooled)),
            "Duplicate source identity in full pool")
    cases=ledger.get("cases")
    require(isinstance(cases,list) and len(cases)==128,
            "The complete 128-case disposition is missing")
    require(set(x["source_id"] for x in cases)==set(selected),
            "Final decisions do not exactly cover frozen selection")
    counters=Counter()
    words_wanted=set()
    target_wanted=set()
    corpus_sources={}
    for row in cases:
        id=row["source_id"]
        kind, name=id.split(":",1)
        require(kind in PATHS and name and "/" not in name and ".." not in name,
                "Unsafe source identity "+id)
        record=load(data/"entities"/PATHS[kind]/(name+".json"))
        require(record["id"]==id and record["bsi"]["source_id"]==id
                and re.fullmatch(r"[0-9a-f]{64}",record["bsi"]["source_sha256"]),
                id+": original source identity or immutable fingerprint invalid")
        require(row.get("outcome") in STATUS,id+": unknown or nonfinal outcome")
        status=row["outcome"]
        counters[status]+=1
        reason=row.get("editorial_conclusion","")
        require(isinstance(reason,str) and len(reason)>=65,
                id+": insufficient source-specific editorial conclusion")
        original=row.get("original_key_verses")
        require(original==selected[id] and len(original)==len(set(original)),
                id+": altered frozen target keys")
        require(set(original).issubset(original_history(record)),
                id+": historical source keys altered without receipt")
        contexts=row.get("source_context")
        require(isinstance(contexts,list)
                and [x.get("verse") for x in contexts]==original,
                id+": every original key needs its own source excerpt")
        for context in contexts:
            v=context["verse"]
            require(re.fullmatch(r"[0-9]{8}",v) is not None,
                    id+": invalid key syntax "+v)
            require(isinstance(context.get("excerpt"),str),
                    id+": missing source excerpt")
            if int(v[:2])!=78:
                target_wanted.add(v)
            else:
                require(context["excerpt"]=="",
                        id+": falsely attributed 1 Maccabees to Macula")
        anchors=row.get("nearby_existing_word_anchors")
        require(isinstance(anchors,list) and len(anchors)<=14,
                id+": invalid source neighbor inventory")
        for link in anchors:
            word=link.get("word_id","")
            vv=link.get("verse")
            require(re.fullmatch(r"[on][0-9]{11,12}",word) is not None
                    and word[1:9]==vv,
                    id+": fabricated word reference "+str(word))
            book,chapter,verse=int(vv[:2]),int(vv[2:5]),int(vv[5:])
            neighbors={f"{book:02d}{chapter:03d}{n:03d}"
                       for key in original
                       if key[:5]==vv[:5]
                       for n in range(max(1,int(key[5:])-2),int(key[5:])+4)}
            require(vv in neighbors,id+": witness is not in original verse context")
            words_wanted.add(word)
        if status=="corrected":
            check_receipt(record,row)
        elif status=="verified_correct":
            require(set(original).issubset(set(record["key_references"])),
                    id+": no-edit claim hides a removed key")
            require(all(int(v[:2])!=78 for v in original),
                    id+": Macula no-edit falsely used for 1 Maccabees")
        elif status=="secondary_verified":
            require(all(int(v[:2])==78 for v in original),
                    id+": secondary proof permitted only for 1 Maccabees")
            sec=row.get("secondary_source",{})
            require(sec.get("url","").startswith("https://")
                    and sec.get("word") and len(sec.get("reason",""))>=65,
                    id+": no documented secondary Greek evidence")
        else:
            require(not row.get("required_receipt_action"),
                    id+": unresolved disguised as edited")
            require(set(original).issubset(set(record["key_references"])),
                    id+": unresolved case was edited without adjudication")
    require(counters["corrected"]>0 and counters["unresolved"]>=0,
            "Cannot infer success from an empty or unresolved-only ledger")
    if (wlc is None)!=(sblgnt is None):
        raise ValueError("Both frozen source TSV paths are required together")
    if wlc is not None:
        # Reconstruct the exact original-language excerpt in source word order.
        # Only emit a 230-character witness slice (not original source redistribution).
        verse_words=defaultdict(list)
        word_by_id={}
        for path in (wlc,sblgnt):
            with Path(path).open(encoding="utf-8-sig",newline="") as stream:
                for word in csv.DictReader(stream,delimiter="\t"):
                    wid=word["xml:id"]
                    if wid[1:9] in target_wanted:
                        verse_words[wid[1:9]].append(
                          (word.get("english") or word.get("gloss") or word.get("text") or "").replace(" ","_"))
                    if wid in words_wanted:
                        require(wid not in word_by_id,"Duplicate pinned source word "+wid)
                        word_by_id[wid]=word["english"]
        require(set(word_by_id)==words_wanted,
                "Cited original word ID missing from the exact frozen editions")
        for row in cases:
            for link in row["nearby_existing_word_anchors"]:
                require(word_by_id[link["word_id"]]==link["english"],
                        row["source_id"]+": source witness English is not pinned")
            for context in row["source_context"]:
                if int(context["verse"][:2])==78:
                    continue
                expected=" ".join(verse_words.get(context["verse"],[]))[:230]
                require(context["excerpt"]==expected,
                        row["source_id"]+": frozen original passage content mismatch "+context["verse"])
    return dict(sorted(counters.items()))|{
      "total":len(cases),"prior_resolved":len(already),
      "resolved_in_pinned_scope":counters["corrected"]+counters["verified_correct"],
      "documented_external_source":counters["secondary_verified"],
      "remaining_unresolved":counters["unresolved"],
      "distinct_witness_word_ids":len(words_wanted)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,default=Path("data"))
    p.add_argument("--ledger",type=Path,default=Path("data/source-key-final-128-review.json"))
    p.add_argument("--wlc",type=Path)
    p.add_argument("--sblgnt",type=Path)
    a=p.parse_args()
    print(json.dumps(validate(a.data,a.ledger,a.wlc,a.sblgnt),sort_keys=True))

if __name__=="__main__":
    main()
