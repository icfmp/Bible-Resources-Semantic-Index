#!/usr/bin/env python3
"""Certify all 63 previously omitted key-only identity/verse decisions.

The original 462 key-only pairs are partitioned into 399 older individually
proven verse decisions and these 63 frozen independent cases. A deleted false
key is proved by an original before/after receipt; an attested name is
restored only as an exact pinned source-word group. Contextual references
are NEVER silently converted into direct names or forced into general refs.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

KIND_DIR={"person":"people","group":"groups","place":"places",
          "deity":"deities","fauna":"fauna","flora":"flora","realia":"realia"}
STATUS={"corrected","verified_contextual"}
HISTORY=("source-key-resolved-115.json","source-key-next-115-resolved.json",
         "source-key-final-128-review.json")
EXPECTED_BASE="861d92fffa1fc69132daa50b85d47cb5e96b21a7"
CORRECTIONS={
    "group:Sidon":"remove_unproven_sidon_joshua_10_6_key",
    "person:Moses":"remove_moses_from_unrelated_matthew_genealogy",
    "place:CityOfDavid":"restore_city_of_david_first_kings_exact_source_word",
    "realia:TempleOfAnIdol":"restore_two_named_idol_temple_original_compounds",
}

def require(ok,reason):
    if not ok:
        raise ValueError(reason)

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def original_keys(row):
    return (row.get("original_key_verses") or row.get("target_key_verses")
            or row.get("key_verses_reviewed"))

def certified_previous(data):
    cases={}
    for name in HISTORY:
        rows=load(data/name)["cases"]
        require(len(rows) in {115,128},"Historical cohort size corrupted")
        for row in rows:
            sid=row["source_id"]
            require(sid not in cases,"Overlapping previously adjudicated source IDs: "+sid)
            require(row["outcome"] in {"corrected","verified_correct","secondary_verified"},
                    "Unresolved old source decision silently promoted: "+sid)
            verses=original_keys(row)
            require(isinstance(verses,list) and
                    len(verses)==len(set(verses)) and
                    all(re.fullmatch(r"[0-9]{8}",v) for v in verses),
                    "Malformed previous original key source verse: "+sid)
            cases[sid]=set(verses)
    require(len(cases)==358,"Corrupt certified original 358-case history")
    return cases

def native_record(data,sid):
    kind,name=sid.split(":",1)
    require(kind in KIND_DIR and re.fullmatch("[A-Za-z0-9_.-]+",name),
            "Invalid historical identity "+sid)
    row=load(data/"entities"/KIND_DIR[kind]/(name+".json"))
    require(row["bsi"]["source_id"]==sid and row["id"]==sid
            and re.fullmatch(r"[0-9a-f]{64}",row["bsi"]["source_sha256"]),
            sid+": historical provenance fingerprint altered")
    return row

def receipt_for(sid,record,action):
    receipts=[x for x in record["bsi"].get("editorial_field_changes",[])
              if x.get("action")==action]
    require(len(receipts)==1 and
            record["bsi"].get("review_status")=="editorially_reviewed",
            sid+": missing unique approved source-native correction receipt")
    x=receipts[0]
    require(isinstance(x.get("reason"),str) and len(x["reason"])>=100
            and isinstance(x.get("evidence"),list) and x["evidence"],
            sid+": insufficient substantive source correction proof")
    changes=x.get("replaced_field_values",{})
    before,after=changes.get("before"),changes.get("after")
    require(isinstance(before,dict) and isinstance(after,dict)
            and before and before!=after and set(before)==set(after),
            sid+": invented/irreversible field change")
    for field,value in after.items():
        require(record.get(field)==value,sid+": source edit receipt drifted in "+field)
    return before,after

def source_verse_neighbors(verse):
    book,chapter,no=int(verse[:2]),int(verse[2:5]),int(verse[5:])
    return {f"{book:02d}{chapter:03d}{n:03d}"
            for n in range(max(1,no-2),no+4)}

def validate(data:Path,ledger_file:Path,wlc:Path|None=None,sblgnt:Path|None=None):
    frozen=load(data/"v1-key-only-remaining-63-candidates.json")
    ledger=load(ledger_file)
    lock=load(data/"source.lock.json")
    require(frozen.get("schema_version")==1
            and frozen.get("source_main_commit")==EXPECTED_BASE
            and frozen.get("previous_certified_case_pairs")==399
            and frozen.get("key_only_pair_count_at_selection")==462
            and frozen.get("previous_certified_source_identity_count")==358,
            "Frozen 63-case source snapshot provenance not intact")
    require(ledger.get("schema_version")==1
            and ledger.get("selection")=="data/v1-key-only-remaining-63-candidates.json"
            and ledger.get("original_main_commit")==EXPECTED_BASE
            and ledger.get("verified_previous_cohort_files")==["data/"+x for x in HISTORY]
            and ledger.get("source_editions")=={
                "wlc":lock["source_editions"]["wlc"]["edition"],
                "sblgnt":lock["source_editions"]["sblgnt"]["edition"]},
            "Final source-review docket changed pins, target selection or source editions")
    old=certified_previous(data)
    selected=frozen.get("cases")
    require(isinstance(selected,list) and len(selected)==30
            and len({c["source_id"] for c in selected})==30,
            "Exactly 30 independently selected historical identities required")
    require(sum(len(c["key_verses"]) for c in selected)==63,
            "Exactly 63 initial never-adjudicated source pairs required")
    choices=ledger.get("cases")
    require(isinstance(choices,list) and len(choices)==30
            and {c["source_id"] for c in choices}==
            {c["source_id"] for c in selected},
            "Docket omitted a frozen entity or added an unrelated record")
    selected_by={x["source_id"]:x for x in selected}
    verdict_by={x["source_id"]:x for x in choices}
    require({x["source_id"] for x in choices if x.get("required_receipt_action")}
            ==set(CORRECTIONS),
            "Corrections must have independent source-specific receipts, not generic statuses")
    all_targets=set()
    pending_original_words=set()
    all_original_contexts=set()
    correction_pairs=set()
    checked=Counter()
    for sid,original in selected_by.items():
        record=native_record(data,sid)
        verdict=verdict_by[sid]
        keys=original["key_verses"]
        require(keys==verdict["original_key_verses"] and
                original["indirect_verse_ids"]==verdict["original_indirect_verses"]
                and len(keys)==len(set(keys)),
                sid+": frozen source key selection was altered")
        require(not set(keys)&old.get(sid,set()),
                sid+": already verified old case silently counted again")
        require(isinstance(verdict.get("editorial_conclusion"),str)
                and len(verdict["editorial_conclusion"])>=155,
                sid+": missing case-specific full narrative examination")
        cases=verdict.get("targets")
        require(isinstance(cases,list) and [x["verse_id"] for x in cases]==keys,
                sid+": an original target key was dropped or reordered")
        before=after=None
        if sid in CORRECTIONS:
            require(verdict["required_receipt_action"]==CORRECTIONS[sid],
                    sid+": false source correction action")
            before,after=receipt_for(sid,record,CORRECTIONS[sid])
        else:
            require("required_receipt_action" not in verdict,
                    sid+": unedited context falsely claims a source patch")
        direct={x for blocks in record["explicit_instances"].values()
                for group in blocks for x in group}
        indirect={x for field in ("pronominal_referents","subject_referents")
                  for blocks in record[field].values()
                  for group in blocks for x in group}
        for target in cases:
            verse=target["verse_id"]
            require(re.fullmatch(r"[0-9]{8}",verse) is not None
                    and int(verse[:2])<=66,
                    sid+": source key outside certified 66-book verse scope")
            pair=(sid,verse)
            require(pair not in all_targets,sid+": repeated source-identity verse")
            all_targets.add(pair)
            all_original_contexts.add(verse)
            excerpt=target.get("locked_source_excerpt")
            require(isinstance(excerpt,str) and bool(excerpt),
                    sid+": missing pinned original source verse excerpt")
            mode=target.get("decision")
            require(mode in STATUS,sid+": a candidate was not actually adjudicated")
            witness_kind=target.get("witness_kind")
            source_words=target.get("word_witnesses")
            require(isinstance(source_words,list) and len(source_words)<=14
                    and len(set(source_words))==len(source_words),
                    sid+": missing or duplicated native contextual word witness group")
            for wid in source_words:
                require(isinstance(wid,str) and re.fullmatch(r"(o[0-9]{12}|n[0-9]{11})",wid),
                        sid+": malformed original source witness")
                require(wid in direct|indirect and wid[1:9] in source_verse_neighbors(verse),
                        sid+": witness neither native nor neighboring the claimed source verse")
                pending_original_words.add(wid)
            new=target.get("restored_exact_word_groups")
            false=target.get("contradicting_original_word_ids")
            if mode=="corrected":
                correction_pairs.add(pair)
                require(before is not None and after is not None,
                        sid+": source-data correction without a review receipt")
                if witness_kind=="false_unrelated_original_key":
                    require(new is None and isinstance(false,list) and false
                            and verse in before.get("key_references",[])
                            and verse not in after.get("key_references",[])
                            and verse not in record["key_references"]
                            and verse not in record["references"],
                            sid+": false key not actually removed or proof not preserved")
                    for wid in false:
                        require(re.fullmatch(r"(o[0-9]{12}|n[0-9]{11})",wid) and
                                wid[1:9]==verse,
                                sid+": alleged contrary name not in target verse")
                        pending_original_words.add(wid)
                elif witness_kind=="restored_complete_original_word_group":
                    require(false is None and isinstance(new,list) and bool(new)
                            and len(new)==len({tuple(group) for group in new})
                            and all(isinstance(group,list) and len(group)>=2
                                    and group in record["explicit_instances"].get("wlc",[])
                                    and group not in before.get("explicit_instances",{}).get("wlc",[])
                                    for group in new)
                            and verse in record["key_references"]
                            and verse not in before.get("references",[])
                            and verse in after.get("references",[]),
                            sid+": original-language name phrases or direct reference not really restored")
                    for group in new:
                        for wid in group:
                            require(isinstance(wid,str) and
                                    re.fullmatch(r"o[0-9]{12}",wid) and wid[1:9]==verse,
                                    sid+": invented/mixed source verse word group")
                            pending_original_words.add(wid)
                else:
                    raise ValueError(sid+": correction lacks direct-name or false-assignment proof")
            else:
                require(witness_kind==(
                    "native_indirect_coreference" if verse in original["indirect_verse_ids"]
                    else "source_specific_context_not_literal_name"),
                    sid+": contextual semantics mislabeled as a direct original name")
                require(new is None and false is None
                        and verse in record["key_references"]
                        and verse not in record["references"],
                        sid+": supposedly unchanged context was silently changed")
            checked[mode]+=1
    require(all_targets=={(s["source_id"],v) for s in selected for v in s["key_verses"]},
            "Key-only original target inventory drifted")
    require(checked=={"corrected":5,"verified_contextual":58} and
            len(correction_pairs)==5,
            "No count-driven success: exactly five proven edits and 58 contextual keys required")
    if (wlc is None)!=(sblgnt is None):
        raise ValueError("Both immutable source corpora required for pinned proof")
    if wlc is not None:
        verse_words=defaultdict(list)
        found=set()
        for file in (wlc,sblgnt):
            with Path(file).open(encoding="utf-8-sig",newline="") as f:
                for word in csv.DictReader(f,delimiter="\t"):
                    wid=word["xml:id"]
                    if wid[1:9] in all_original_contexts:
                        verse_words[wid[1:9]].append(
                            (word.get("english") or word.get("gloss") or
                             word.get("text") or "").replace(" ","_"))
                    if wid in pending_original_words:
                        require(wid not in found,"Repeated original source word ID "+wid)
                        found.add(wid)
        require(found==pending_original_words,
                "Original named source word not found in locked WLC/SBLGNT inventory")
        for item in choices:
            for target in item["targets"]:
                verse=target["verse_id"]
                expected=" ".join(verse_words[verse])[:230]
                require(target["locked_source_excerpt"]==expected,
                        item["source_id"]+": independently re-collated original verse differs "+verse)
    return {"total":len(all_targets),"source_id_groups":len(selected),
            "corrected_pairs":checked["corrected"],"corrected_source_records":len(CORRECTIONS),
            "verified_contextual_pairs":checked["verified_contextual"],
            "prior_proven_source_identities":len(old),
            "previously_certified_current_pairs_at_snapshot":399,
            "previous_key_only_pairs_at_snapshot":462,
            "distinct_cited_original_word_ids":len(pending_original_words),
            "remaining_unadjudicated_in_frozen_population":0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",type=Path,default=Path("data"))
    p.add_argument("--ledger",type=Path,default=Path("data/v1-key-only-final-63-review.json"))
    p.add_argument("--wlc",type=Path)
    p.add_argument("--sblgnt",type=Path)
    x=p.parse_args()
    print("BRSi_LAST_KEY_ONLY_SOURCE_REVIEW "+json.dumps(
        validate(x.data,x.ledger,x.wlc,x.sblgnt),sort_keys=True))

if __name__=="__main__":
    main()
