#!/usr/bin/env python3
"""Nonpublishing source-constituent × French lexical neighborhood hypotheses.

Original MACULA lowfat XML supplies real syntactic source phrase boundaries.
Existing independently attested target anchors and lemma distributions from
OTHER verses supply candidate authored French spans. This is an attempt at
bilingual *review localization*, not independently verified translation.

Validation masks one direct Clear.Bible NT source-to-French target in each of
600 distinct verses; ALL source IDs sharing that exact target are hidden
from anchor construction and ALL 600 verses are excluded from the learned
lemma→French surface distributions. Source links, indices and Scripture are
never modified. A prior lexical study used related Clear.Bible sources, so
this remains retrospective positional pseudo-gold, not blind human gold.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "brsi_syntax_neighborhood_diverse",
    ROOT / "scripts" / "audit_macula_lsg_diverse_syntax.py")
diverse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diverse)
syntax = diverse.syntax
phrase = syntax.phrase
bridge = syntax.bridge
lexical = phrase.lexical
sampler = syntax.sampler

MAX_FRENCH_SPAN = 16
NT_TEST_VERSES = 600
RADII = (2, 4, 8)
LEXICAL_GATES = ((3, .5), (5, .6), (8, .7), (12, .8))
# A threshold requires independent distinct NT verses, not only easy wins.
MIN_CALIBRATION_ATTEMPTS = 25
MIN_BLIND_ATTEMPTS = 25
MIN_EXACT_PRECISION = .95
MIN_WILSON95_LOWER = .84


def syntax_families(parsed: list[dict]) -> tuple[dict, dict]:
    """Real original source XML <wg> ancestor families, not token adjacency."""
    by_source: dict[str, list[dict]] = collections.defaultdict(list)
    doc_by_verse: dict[str, dict] = {}
    for doc in parsed:
        for verse in doc["verses"]:
            if verse in doc_by_verse:
                raise ValueError("original XML verse appears in more than one source")
            doc_by_verse[verse] = doc
        for group in doc["all_eligible_constituents"]:
            for source in group["original_macula_ids"]:
                if syntax.source_verse(source) != group["source_verse"]:
                    raise ValueError("cross-verse original constituent")
                by_source[source].append(group)
    for source in by_source:
        by_source[source].sort(
            key=lambda g: (len(g["original_macula_ids"]),
                           -g["original_source_syntax_depth"], g["group_id"]))
    return dict(by_source), doc_by_verse


def original_group_anchors(
        index: dict, sources: list[str], word_count: int,
        *, hidden_source: str | None = None,
        hidden_word: str | None = None) -> list[tuple[str, str, int]]:
    """Use *existing* indexed anchors; never reassign missing source words."""
    anchors = []
    for original in sources:
        result = phrase.exact_anchor(
            index, original, hidden_source=hidden_source,
            hidden_french_word=hidden_word)
        if result is None:
            continue
        word_id, ordinal = result
        if ordinal > word_count:
            raise ValueError("original anchor exceeds exact French authored word count")
        anchors.append((original, word_id, ordinal))
    return anchors


def candidate(
        index: dict, authored: dict[str, str], source: str,
        groups: list[dict], lexical_guess: dict | None,
        *, radius: int = 4,
        hidden_source: str | None = None,
        hidden_word: str | None = None,
        cache: dict[str, list[str]] | None = None) -> dict | None:
    """Constrain a lemma candidate by authentic source syntax neighbors.

    The phrase includes the selected existing French anchors and a
    *lexically hypothesized* French word near at least one of them.
    It can expand either side, representing reordering and one-to-many
    grammatical groupings. It does NOT prove phrase translation.
    """
    if radius < 0 or not lexical_guess or not groups:
        return None
    word_id = lexical_guess.get("word_id", "")
    verse = syntax.source_verse(source)
    if not word_id.startswith(verse+":"):
        raise ValueError("lemma hypothesis references another French verse")
    raw = word_id.partition(":")[2]
    if not raw.isdecimal() or int(raw) < 1:
        raise ValueError("invalid authored French lemma target ID")
    ordinal = int(raw)
    if cache is None:
        cache = {}
    french = lexical.words_in_verse(verse, authored, cache)
    if ordinal > len(french):
        raise ValueError("lemma hypothesis beyond exact authored French text")
    proposals = []
    for group in groups:
        if group["source_verse"] != verse or source not in group["original_macula_ids"]:
            raise ValueError("source not present in original constituent or verse")
        anchors = original_group_anchors(
            index, group["original_macula_ids"], len(french),
            hidden_source=hidden_source, hidden_word=hidden_word)
        if not anchors:
            continue
        if min(abs(ordinal - a[2]) for a in anchors) > radius:
            continue
        positions = [a[2] for a in anchors]
        first, last = min(positions+[ordinal]), max(positions+[ordinal])
        if last-first+1 > MAX_FRENCH_SPAN:
            continue
        if hidden_word and hidden_word in [a[1] for a in anchors]:
            raise ValueError("heldout exact French word leaked into source anchor")
        proposal = {
            "original_macula_id_under_review": source,
            "original_source_verse": verse,
            "original_source_constituent_id": group["group_id"],
            "original_macula_phrase_ids": group["original_macula_ids"],
            "original_syntax_class": group["original_group_class"],
            "original_syntax_rule": group["original_group_rule"],
            "original_syntax_role": group["original_group_role"],
            "existing_source_french_anchors": [
                {"original_macula_id": s, "lsg_word_id": word}
                for s, word, _ in anchors],
            "lexical_source_lemma_candidate_french_word_id": word_id,
            "candidate_authored_french_phrase_word_ids": [
                f"{verse}:{i}" for i in range(first, last+1)],
            "original_phrase_has_source_syntax_evidence": True,
            "french_word_support_other_source_verses":
                lexical_guess["support_independent_source_verses"],
            "french_word_support_share": lexical_guess["share"],
            "source_verse_shared_with_training": False,
            "human_semantic_gold": False,
            "french_span_is_not_verified_translation": True,
            "automatic_word_or_phrase_links_approved": 0,
            "publication_authorized": False,
        }
        proposals.append((
            len(group["original_macula_ids"]), last-first+1,
            min(abs(ordinal-a[2]) for a in anchors),
            group["group_id"], proposal))
    if not proposals:
        return None
    # Choose smallest actual original-language constituent, then shorter
    # exact French span; this choice NEVER uses the hidden gold answer.
    proposals.sort(key=lambda x: x[:4])
    return proposals[0][4]


def select_nt_pseudo_gold(index: dict, pivots: dict, authored: dict,
                          doc_by_verse: dict, n: int = NT_TEST_VERSES) -> dict:
    """Distinct NT original verses from fixed complete Greek source witnesses."""
    eligible = {}
    for verse, doc in sorted(doc_by_verse.items()):
        if doc["canon"] != "nt" or verse not in authored:
            continue
        options = []
        for source in doc["verses"][verse]:
            if source not in pivots["nt"] or not pivots["nt"][source][0]:
                continue
            word = lexical.one_word_id(index, source, direct_only=True)
            if word is not None:
                options.append((source, word))
        if options:
            eligible[verse] = min(options, key=lambda x: lexical.stable_key(x[0]))
    if len(eligible) < n or n % 2:
        raise ValueError("insufficient independent NT exact-source witness verses")
    verses = sorted(eligible, key=lexical.stable_key)[:n]
    return dict(eligible[verse] for verse in verses)


def one_metric(gold: dict[str, str], guesses: dict, family: dict,
               radius: int, threshold: tuple[int, float]) -> dict:
    if set(gold) != set(guesses):
        raise ValueError("wrong heldout original IDs")
    correct = covered = total_words = 0
    n = 0
    source_group_sizes = collections.Counter()
    for source, answer in gold.items():
        lexical_guess, proposed = guesses[source]
        if not lexical.qualifies(lexical_guess, threshold) or proposed is None:
            continue
        # A candidate built under a wider radius is not valid for a
        # narrower requested evaluation radius.
        delta = min(
            abs(int(answer_position["lsg_word_id"].split(":")[1]) -
                int(lexical_guess["word_id"].split(":")[1]))
            for answer_position in proposed["existing_source_french_anchors"])
        if delta > radius:
            continue
        n += 1
        correct += int(lexical_guess["word_id"] == answer)
        covered += int(answer in proposed["candidate_authored_french_phrase_word_ids"])
        total_words += len(proposed["candidate_authored_french_phrase_word_ids"])
        source_group_sizes[len(proposed["original_macula_phrase_ids"])] += 1
    p = correct/n if n else 0.
    import math
    z = 1.96
    den = 1+z*z/n if n else 1.
    low = ((p + z*z/(2*n) - z*math.sqrt(
        p*(1-p)/n+z*z/(4*n*n))) / den) if n else 0.
    return {
        "cases": len(gold), "attempted": n,
        "word_exact_correct": correct, "word_exact_wrong": n-correct,
        "candidate_phrase_contains_pseudo_gold_word": covered,
        "candidate_phrase_misses_pseudo_gold_word": n-covered,
        "abstained": len(gold)-n,
        "exact_word_precision": round(p,5),
        "wilson95_lower": round(low,5),
        "phrase_containment_rate_not_semantic_phrase_accuracy":
            round(covered/n,5) if n else 0,
        "mean_candidate_french_phrase_word_count":
            round(total_words/n,4) if n else 0,
        "source_group_size_distribution": dict(sorted(source_group_sizes.items())),
        "candidate_rate": round(n/len(gold),5) if gold else 0,
    }


def gold_analysis(index: dict, pivots: dict, authored: dict,
                  source_groups: dict, doc_by_verse: dict) -> tuple[dict,dict,dict,dict]:
    gold = select_nt_pseudo_gold(index, pivots, authored, doc_by_verse)
    frozen_verses = {syntax.source_verse(s) for s in gold}
    if len(gold) != NT_TEST_VERSES or len(frozen_verses) != NT_TEST_VERSES:
        raise ValueError("heldout verse-level pseudo-gold selection changed")
    buckets, training = lexical.lexical_buckets(
        index, pivots, authored, frozen_verses)
    predictions = {}
    french_cache = {}
    for original in sorted(gold):
        actual = gold[original]
        # Explicit masking must remove original ID and *all other source IDs*
        # which point to the same actual French word in the source group.
        guess = lexical.predict(
            original, pivots["nt"], authored, french_cache, buckets)
        proposal = candidate(
            index, authored, original, source_groups.get(original, []),
            guess, radius=max(RADII), hidden_source=original,
            hidden_word=actual, cache=french_cache)
        predictions[original] = (guess, proposal)
        if proposal:
            assert all(a["lsg_word_id"] != actual
                       for a in proposal["existing_source_french_anchors"])
    ordered = sorted(gold, key=lexical.stable_key)
    halves = [
        {s:gold[s] for s in ordered[:len(ordered)//2]},
        {s:gold[s] for s in ordered[len(ordered)//2:]},
    ]
    grid = []
    eligible = []
    for radius in RADII:
        # Recreate the candidates at the predeclared radius instead
        # of only filtering a wider-radius preferred group afterward.
        cal_guesses = {}
        blind_guesses = {}
        for i, subset in enumerate(halves):
            target = cal_guesses if i == 0 else blind_guesses
            for source in subset:
                lex, _ = predictions[source]
                tested = candidate(
                    index, authored, source, source_groups.get(source, []),
                    lex, radius=radius, hidden_source=source,
                    hidden_word=gold[source], cache=french_cache)
                target[source] = (lex, tested)
        for threshold in LEXICAL_GATES:
            cal = one_metric(halves[0], cal_guesses, source_groups, radius, threshold)
            grid.append({"radius":radius,"minimum_lemma_source_verses":threshold[0],
                         "minimum_lemma_share":threshold[1],**cal})
            if (cal["attempted"] >= MIN_CALIBRATION_ATTEMPTS and
                cal["exact_word_precision"] >= MIN_EXACT_PRECISION and
                cal["wilson95_lower"] >= MIN_WILSON95_LOWER):
                eligible.append((-cal["attempted"], -cal["wilson95_lower"],
                                 radius, threshold))
    if eligible:
        best = sorted(eligible)[0]
        chosen = {"radius":best[2], "min_source_verses":best[3][0],
                  "min_lemma_share":best[3][1]}
        test = {
            s:(predictions[s][0],candidate(
                index, authored, s, source_groups.get(s, []),
                predictions[s][0], radius=chosen["radius"],
                hidden_source=s, hidden_word=gold[s], cache=french_cache))
            for s in halves[1]}
        blind = one_metric(halves[1],test,source_groups,chosen["radius"],best[3])
    else:
        chosen = None
        blind = one_metric(
            halves[1],{s:(None,None) for s in halves[1]},
            source_groups, RADII[0], LEXICAL_GATES[0])
    controls = []
    for radius in RADII:
        for subset in halves:
            tested = {
                s:(predictions[s][0],candidate(
                    index, authored, s, source_groups.get(s, []),
                    predictions[s][0], radius=radius,
                    hidden_source=s, hidden_word=gold[s], cache=french_cache))
                for s in subset}
            controls.append({
                "radius":radius,"cohort":"calibration" if subset is halves[0]
                else "retrospective_reporting",
                "predeclared_exploratory":True,
                **one_metric(subset,tested,source_groups,radius,LEXICAL_GATES[0])})
    passing = bool(
        chosen and blind["attempted"] >= MIN_BLIND_ATTEMPTS and
        blind["exact_word_precision"] >= MIN_EXACT_PRECISION and
        blind["wilson95_lower"] >= MIN_WILSON95_LOWER)
    return ({
        "pseudo_gold_total":len(gold),
        "distinct_source_verses":len(frozen_verses),
        "calibration_verses":len(halves[0]), "reporting_verses":len(halves[1]),
        "all_heldout_verses_excluded_from_lemma_training":True,
        "masked_source_and_all_same_French_word_anchors":True,
        "not_fresh_prospectively_blinded":True,
        "does_not_measure_human_phrase_semantics":True,
        "calibration_grid":grid,
        "threshold_selected_only_from_calibration":chosen,
        "selected_gate_reporting":blind,
        "selected_predeclared_gate_passed":passing,
        "exploratory_radius_controls":controls,
    }, buckets, training, gold)


def unresolved_review_hypotheses(
        index:dict, pivots:dict, authored:dict,
        source_groups:dict, doc_by_verse:dict,
        buckets:dict, *, radius:int=4,
        threshold:tuple[int,float]=(3,.5)) -> tuple[list[dict],dict]:
    unresolved = index["unlinked_cause_by_original_macula_id"]
    cases = []
    counts = collections.defaultdict(collections.Counter)
    french_cache = {}
    for original in sorted(source_groups):
        if original not in unresolved:
            continue
        verse = syntax.source_verse(original)
        doc = doc_by_verse[verse]
        canon=doc["canon"]
        cause=unresolved[original]
        counts[(canon,cause)]["source_unlinked_with_original_XML_group"] += 1
        guess = lexical.predict(
            original, pivots[canon], authored, french_cache, buckets)
        if not lexical.qualifies(guess, threshold):
            counts[(canon,cause)]["lemma_lexicon_no_eligible_word"] += 1
            continue
        counts[(canon,cause)]["lemma_lexicon_eligible_word"] += 1
        matched = candidate(
            index, authored, original, source_groups[original], guess,
            radius=radius, cache=french_cache)
        if not matched:
            counts[(canon,cause)]["no_local_supported_original_phrase"] += 1
            continue
        counts[(canon,cause)]["syntactic_french_span_review_hypothesis"] += 1
        counts[(canon,cause)]["word_span_sum"] += len(
            matched["candidate_authored_french_phrase_word_ids"])
        matched["unlinked_reason"]=cause
        matched["canon"]=canon
        matched["lemma_id_sha256"]=hashlib.sha256(
            pivots[canon][original][0].encode("utf-8")).hexdigest()
        matched["source_original_text"]=doc["tokens"][original]["original_surface"]
        matched["authored_lsg_verse"]=authored[verse]
        matched["lexical_french_candidate_surface"]=french_cache[verse][
            int(guess["word_id"].split(":")[1])-1]
        cases.append(matched)
    for canon in ("nt","ot"):
        for cause in sampler.STRATA:
            counts[(canon,cause)]["total_pinned_original_unlinked_in_scope"] = sum(
                1 for source in unresolved if source in doc_by_verse.get(
                    syntax.source_verse(source), {}).get("tokens", {})
                and source.startswith("n" if canon=="nt" else "o")
                and unresolved[source]==cause)
    report={canon:{
        cause:dict(sorted(counts[(canon,cause)].items()))
        for cause in sampler.STRATA} for canon in ("nt","ot")}
    return cases, report


def run(index:dict, pivots:dict, authored:dict,
        parsed:list[dict]) -> tuple[dict,dict]:
    source_groups, books = syntax_families(parsed)
    validation, buckets, training, gold = gold_analysis(
        index, pivots, authored, source_groups, books)
    # This predeclared exploration is NOT selected by blind outcomes:
    # four-neighbor French-word radius and the first frozen lexical gate.
    cases, strata = unresolved_review_hypotheses(
        index,pivots,authored,source_groups,books,buckets,
        radius=4, threshold=(3,.5))
    group_ids = {c["original_source_constituent_id"] for c in cases}
    per_canon=collections.Counter(c["canon"] for c in cases)
    baseline = index["unlinked_cause_by_original_macula_id"]
    scope = {s for s in baseline if syntax.source_verse(s) in books
             and s in books[syntax.source_verse(s)]["tokens"]}
    if sum(c["total_pinned_original_unlinked_in_scope"]
           for v in strata.values() for c in v.values()) != len(scope):
        raise ValueError("unresolved original-ID scope changed")
    if len(set(c["original_macula_id_under_review"] for c in cases))!=len(cases):
        raise ValueError("duplicate original-ID French span hypotheses")
    if any(c["original_macula_id_under_review"] not in scope or
           c["automatic_word_or_phrase_links_approved"]!=0 or
           not c["french_span_is_not_verified_translation"]
           for c in cases):
        raise ValueError("hypotheses changed original ID scope or approval status")
    report={
        "kind":"brsi-macula-source-syntax-local-lexical-bilingual-candidate-negative-control",
        "schema_version":1,
        "source_scope":"18_pinned_original_mixed_genre_lowfat_XML_witnesses",
        "source_original_XML_file_count":len(parsed),
        "source_original_verse_count":len(books),
        "original_index_full_MACULA_ID_count":len(index["by_original_macula_id"]),
        "original_index_french_word_candidate_ID_count":(
            len(index["by_original_macula_id"])-len(baseline)),
        "original_index_unlinked_ID_count":len(baseline),
        "original_unlinked_IDs_in_XML_scope":len(scope),
        "unresolved_with_eligible_original_syntax_families":
            sum(source in source_groups for source in scope),
        "candidate_source_original_IDs":len(cases),
        "candidate_distinct_MACULA_original_constituent_IDs":len(group_ids),
        "candidate_original_IDs_by_canon":dict(sorted(per_canon.items())),
        "candidate_by_stratum":strata,
        "local_authorial_french_phrase_word_limit":MAX_FRENCH_SPAN,
        "single_preset_exploration_anchor_radius_french_words":4,
        "single_preset_exploration_lemma_threshold":{
            "min_independent_source_verse_support":3,"min_share":.5,
            "min_margin":.15},
        "lexical_training_source_counts":training,
        "ot_lexical_training_uses_unreviewed_Aquifer_original_word_candidates":True,
        "evaluation":validation,
        "existing_french_anchors_and_lemma_model_not_fully_independent":True,
        "local_lemma_guess_NOT_human_semantic_word_equivalence":True,
        "original_syntax_plus_french_span_NOT_human_phrase_equivalence":True,
        "human_reviewed_original_to_french_semantic_gold":0,
        "automatic_approved_new_source_target_links":0,
        "original_text_or_lsg_modified":False,
        "publication_authorized":False,
        "report_includes_private_original_or_authored_french_text":False,
    }
    private={
        "kind":"brsi-private-macula-lexical-neighborhood-source-phrase-review",
        "original_review_candidate_ids":cases,
        "pseudo_gold_masked_source_word_ids":gold,
        "source_original_lemma_training_excludes_600_NT_pseudo_gold_verses":True,
        "automatic_approved_new_source_target_links":0,
        "publication_authorized":False,
    }
    return private,report


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for name in (
        "original-index","correspondence-lock","pivot-lock","pivot-nt",
        "pivot-ot","curated-lock","curated-root","original-nt-root",
        "original-ot-root","private-candidates","report"):
        p.add_argument("--"+name,required=True,type=Path)
    args=p.parse_args()
    for path in (args.private_candidates,args.report):
        if path.resolve().is_relative_to(ROOT):
            raise ValueError("private original/LSG candidate outputs cannot reside in tracked tree")
    if args.report.resolve()==args.private_candidates.resolve():
        raise ValueError("source-free and private outputs must be separate")
    source_lock=json.loads(args.correspondence_lock.read_text(encoding="utf-8"))
    index,index_sha=phrase.pinned_index(args.original_index,source_lock)
    curated=json.loads(args.curated_lock.read_text(encoding="utf-8"))
    if curated["osis_sha256"] != source_lock["curated_osis_sha256"]:
        raise ValueError("source exact authored French LSG edition changed")
    pivot_lock=json.loads(args.pivot_lock.read_text(encoding="utf-8"))
    pivots={}
    for canon,path in (("nt",args.pivot_nt),("ot",args.pivot_ot)):
        pivots[canon],_=lexical.pivot_source(
            path,canon,pivot_lock["sources"][canon]["sha256"])
    french_path=bridge.ed.pinned_file(
        args.curated_root,curated["osis_path"],curated["osis_sha256"])
    authored=bridge.ed.read_osis(french_path)
    parsed=[]
    for canon,filename,_ in diverse.BREADTH_SOURCES:
        filepath=((args.original_nt_root if canon=="nt" else
                   args.original_ot_root)/filename)
        parsed.append(syntax.parse_original_syntax(
            filepath.read_bytes(),canon,filename))
    private,report=run(index,pivots,authored,parsed)
    packed=phrase.compressed_private(private)
    report.update({
        "full_source_index_gzip_sha256":index_sha,
        "source_clear_bible_revision":source_lock["source_clear_bible_revision"],
        "source_aquifer_revision":source_lock["source_aquifer_revision"],
        "authored_LSG_1_0_2_OSIS_sha256":curated["osis_sha256"],
        "macula_original_source_revisions":{
            canon:pivot_lock["sources"][canon]["revision"]
            for canon in ("nt","ot")},
        "source_original_lowfat_XML_file_sha256":{
            d["source_file"]:d["source_xml_sha256"] for d in parsed},
        "private_candidates_gzip_sha256":hashlib.sha256(packed).hexdigest(),
        "private_candidates_gzip_bytes":len(packed),
    })
    args.private_candidates.write_bytes(packed)
    args.report.write_text(json.dumps(
        report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("BRSI_MACULA_SYNTAX_LOCAL_LEXICAL_SOURCE_FREE_REPORT")
    print(args.report.read_text(encoding="utf-8"))


if __name__=="__main__":
    main()
