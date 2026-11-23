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
    require(ledger["frozen_selection"]=="data/source-key-final-128-candidates.json"
            and ledger["frozen_pool"]=="data/source-key-unresolved-queue.json"
            and ledger["previous_resolved"]==[
               "data/source-key-resolved-115.json",
               "data/source-key-next-115-resolved.json"],
            "Frozen ledger provenance paths cannot be redirected")
    select=load(data/"source-key-final-128-candidates.json")
    pool=load(data/"source-key-unresolved-queue.json")
    a=load(data/"source-key-resolved-115.json")
    b=load(data/"source-key-next-115-resolved.json")
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
    last_batch=load(data/"source-key-last-12-candidates.json")
    require(last_batch.get("schema_version")==1
            and last_batch.get("from_merged_commit")=="1aad2adfffe0afba0d25d361243429cb4c0d7977"
            and last_batch.get("parent_register")=="data/source-key-final-128-review.json",
            "Last-twelve frozen source/commit provenance changed")
    last_items=last_batch.get("cases")
    require(isinstance(last_items,list) and len(last_items)==12
            and len(set(x["source_id"] for x in last_items))==12,
            "The 12 original editorial holds were silently omitted or duplicated")
    last_ids={x["source_id"]:x["original_key_verses"] for x in last_items}
    require(all(k in selected and selected[k]==v for k,v in last_ids.items()),
            "Final original-key identities no longer match frozen historical selection")
    cases=ledger.get("cases")
    require(isinstance(cases,list) and len(cases)==128,
            "The complete 128-case disposition is missing")
    require(set(x["source_id"] for x in cases)==set(selected),
            "Final decisions do not exactly cover frozen selection")
    require({x["source_id"] for x in cases if "source_proof" in x}==set(last_ids),
            "Last twelve decisions lack dedicated evidence or evidence was added to unrelated cases")
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
        proof=row.get("source_proof")
        if id in last_ids:
            require(status in {"corrected","verified_correct"},
                    id+": previously unresolved identity is not independently settled")
            require(row["original_key_verses"]==last_ids[id],
                    id+": final hold's exact historical keys drifted")
            require(isinstance(proof,dict),id+": missing complete final proof")
            ids=proof.get("pinned_word_ids")
            require(isinstance(ids,list) and bool(ids) and len(ids)==len(set(ids)),
                    id+": no unique original-language identity witnesses")
            for wid in ids:
                require(isinstance(wid,str) and re.fullmatch(r"(o[0-9]{12}|n[0-9]{11})",wid),
                        id+": invalid original source word ID "+str(wid))
                book=int(wid[1:3])
                require((1<=book<=39 if wid.startswith("o") else 40<=book<=66),
                        id+": word claimed in wrong corpus")
                words_wanted.add(wid)
            urls=proof.get("independent_references")
            require(isinstance(urls,list) and bool(urls) and
                    all(isinstance(url,str) and url.startswith("https://")
                        and " " not in url for url in urls),
                    id+": independent contextual evidence absent or malformed")
            require(isinstance(proof.get("interpretation"),str)
                    and proof["interpretation"]==reason
                    and len(reason)>=110,
                    id+": editorial conclusion and original-source evidence disagree")
            expected=("reversible_correction_with_pinned_source_lexemes"
                      if status=="corrected" else
                      "contextual_or_interpretive_no_new_name_word")
            require(proof.get("claimed_relation")==expected,
                    id+": unsupported direct versus contextual witness claim")
            for extra in proof.get("reassigned_to",[]):
                require(isinstance(extra,str) and extra.count(":")==1,
                        id+": malformed reassigned historical identity")
                e_kind,e_name=extra.split(":")
                require(e_kind in PATHS,id+": reassigned entity category missing")
                erow=load(data/"entities"/PATHS[e_kind]/(e_name+".json"))
                require(erow["id"]==extra and erow["bsi"]["source_id"]==extra,
                        id+": false purported destination identity")
                targetwords={w for blocks in erow["explicit_instances"].values()
                             for group in blocks for w in group}
                require(bool(set(ids)&targetwords),
                        id+": no genuine reassigned original-language word link")
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
      "distinct_witness_word_ids":len(words_wanted),
      "final_twelve_proven":len(last_ids),
      "last_twelve_reversible":sum(1 for r in cases
          if r["source_id"] in last_ids and r["outcome"]=="corrected"),
      "last_twelve_contextual":sum(1 for r in cases
          if r["source_id"] in last_ids and r["outcome"]=="verified_correct")}

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
