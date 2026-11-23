#!/usr/bin/env python3
"""Negative tests for original UBS explicit bilingual alternative Greek lemmas."""
import copy,runpy,unittest
from pathlib import Path

MOD=runpy.run_path(str(Path(__file__).with_name("audit_ubs_explicit_alternate_lemmas.py")))

def fixture():
    en=[{"MainId":"A","Lemma":"Ἱεροσόλυμα",
         "AlternateLemmas":["Ἰερουσαλήμ"],
         "BaseForms":[{"PartsOfSpeech":["noun-name, f./n."],
                       "LEXMeanings":[{"LEXEntryCode":"93.480a"}]}],
         "StrongCodes":["G2414"]}]
    fr=copy.deepcopy(en)
    report={"status":"PRIVATE_Greek_456_original_word_ubs_v1_variants_READ_ONLY_NOT_APPROVED",
            "original_word_count":456,
            "new_source_lexical_headword_links":0,"publication_approved":False,
            "source_editions":{"ubs_greek_edition":"1.0"}}
    report["families"]=[
        {"original_lemma":"Ἰερουσαλήμ","original_strong":"2419",
         "original_word_ids":[f"n{i:011d}" for i in range(456)],
         "original_words":456,
         "original_word_witnesses":[{"original_word_id":f"n{i:011d}","original_ln":"93.480a","original_lemma":"Ἰερουσαλήμ","original_strong":"2419"} for i in range(456)],
         "original_ln_counts":{"93.480a":456},
         "original_class_counts":{"noun":456}}]
    return report,en,fr


def source_459_fixture():
    """Synthetic historical partition: 3 separately reviewed, 456 still unlinked."""
    report, _, _ = fixture()
    residual = report["families"][0]
    alpha_witnesses = [
        {"original_word_id":f"n{i:011d}", "original_lemma":"Ἄλφα",
         "original_strong":"1", "original_ln":""}
        for i in range(456,459)
    ]
    return {
        "status":"PRIVATE_459_UBS_Greek_v1_0_missing_exact_headword_source_evidence_ONLY",
        "original_words":459,
        "automatic_lemma_mappings_approved":0,
        "inferred_contextual_senses":0,
        "modified_original_greek_or_strong":False,
        "historical_index_modified":False,
        "publication_approved":False,
        "source_editions":report["source_editions"],
        "source_word_families":[
            {"original_greek_lemma_nfc_for_comparison":residual["original_lemma"],
             "original_source_strong":residual["original_strong"],
             "original_word_count":456,
             "source_original_word_witnesses":residual["original_word_witnesses"],
             "original_ln_code_counts":residual["original_ln_counts"],
             "original_source_classes":residual["original_class_counts"],
             "ubs_case_only_spelling_main_ids":[],
             "classification":"no_lexeme_spelling_or_strong_equivalence_in_pinned_UBS"},
            {"original_greek_lemma_nfc_for_comparison":"Ἄλφα",
             "original_source_strong":"1",
             "original_word_count":3,
             "source_original_word_witnesses":alpha_witnesses,
             "original_ln_code_counts":{},
             "original_source_classes":{"noun":3},
             "ubs_case_only_spelling_main_ids":["A"],
             "classification":"case_insensitive_Ubs_spelling_present_NOT_APPROVED"},
        ],
    }

class OriginalBilingualUBSAlternateLemmas(unittest.TestCase):
    def test_only_source_explicit_lemmas_qualify(self):
        r,en,fr=fixture()
        out=MOD["audit"](r,en,fr)
        self.assertEqual(out["source_evidence_counts"],
                         {"exact_original_ubs_alternate_lemma_and_ln":456})
        self.assertEqual(out["new_source_word_lexical_headwords_approved"],0)
        self.assertEqual(len(out["source_families"][0]["original_ubs_explicit_alternate_headwords"][0]["original_word_ids_with_bilingual_source_ln"]),456)
        self.assertEqual(out["source_families"][0]["original_ubs_explicit_alternate_headwords"][0]["ubs_original_main_id"],"A")

    def test_similar_but_not_original_alternate_is_not_identity(self):
        r,en,fr=fixture()
        en[0]["AlternateLemmas"]=fr[0]["AlternateLemmas"]=[]
        out=MOD["audit"](r,en,fr)
        self.assertEqual(out["source_evidence_counts"],{"not_in_original_ubs_alternate_lemmas":456})

    def test_inflection_metadata_is_not_an_explicit_lexical_identity(self):
        # A similar inflection and the same LN domain are not source-approved
        # alternate lemmas. This is a reusable exclusion, not a 47-word probe.
        r,en,fr=fixture()
        en[0]["AlternateLemmas"]=fr[0]["AlternateLemmas"]=[]
        en[0]["BaseForms"][0]["Inflections"]=["Ἰερουσαλήμ"]
        fr[0]["BaseForms"][0]["Inflections"]=["Ἰερουσαλήμ"]
        out=MOD["audit"](r,en,fr)
        self.assertEqual(out["source_evidence_counts"],
                         {"not_in_original_ubs_alternate_lemmas":456})
        self.assertEqual(out["new_source_word_lexical_headwords_approved"],0)

    def test_bilingual_alternate_drift_rejected(self):
        r,en,fr=fixture()
        fr[0]["AlternateLemmas"]=[]
        with self.assertRaisesRegex(ValueError,"alternate or LN"):
            MOD["audit"](r,en,fr)

    def test_bilingual_source_lexical_ln_drift_rejected(self):
        r,en,fr=fixture()
        fr[0]["BaseForms"][0]["LEXMeanings"][0]["LEXEntryCode"]="93.481"
        with self.assertRaisesRegex(ValueError,"alternate or LN"):
            MOD["audit"](r,en,fr)

    def test_missing_original_ln_keeps_candidate_unapproved(self):
        r,en,fr=fixture()
        r["families"][0]["original_ln_counts"]={}
        for word in r["families"][0]["original_word_witnesses"]:word["original_ln"]=""
        out=MOD["audit"](r,en,fr)
        self.assertEqual(out["source_evidence_counts"],
                         {"exact_original_ubs_alternate_lemma_NO_corresponding_source_ln":456})


    def test_project_missing_source_keeps_all_456_original_witnesses(self):
        source=source_459_fixture()
        projected=MOD["project_unapproved_source_words"](source)
        self.assertEqual(projected["original_word_count"],456)
        self.assertEqual(len(projected["families"]),1)
        self.assertEqual(projected["families"][0]["original_word_ids"],
                         [f"n{i:011d}" for i in range(456)])
        self.assertEqual(projected["source_editions"],source["source_editions"])
        self.assertEqual(projected["new_source_lexical_headword_links"],0)
        self.assertFalse(projected["publication_approved"])
        # No accentless or original-Strong guess is inserted into the
        # source-explicit bilingual alternate lemma algorithm.
        _,en,fr=fixture()
        results=MOD["audit"](projected,en,fr)
        self.assertEqual(results["source_evidence_counts"],
                         {"exact_original_ubs_alternate_lemma_and_ln":456})
        self.assertFalse(results["publication_approved"])

    def test_frozen_459_source_drift_and_case_only_partition_rejected(self):
        original=source_459_fixture()
        for key,val in [("publication_approved",True),
                        ("automatic_lemma_mappings_approved",1),
                        ("inferred_contextual_senses",1),
                        ("historical_index_modified",True)]:
            item=copy.deepcopy(original)
            item[key]=val
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"source report drift"):
                MOD["project_unapproved_source_words"](item)
        bad=copy.deepcopy(original)
        bad["source_word_families"][1]["ubs_case_only_spelling_main_ids"]=[]
        with self.assertRaisesRegex(ValueError,"No approved Greek Strong or spelling"):
            MOD["project_unapproved_source_words"](bad)
        bad=copy.deepcopy(original)
        bad["source_word_families"][1]["source_original_word_witnesses"][0]["original_word_id"]="n00000000000"
        with self.assertRaisesRegex(ValueError,"Duplicate or altered"):
            MOD["project_unapproved_source_words"](bad)

    def test_accentless_spelling_and_same_ln_never_make_ubs_alternate(self):
        report,en,fr=fixture()
        # NFD stripping yields a superficially similar source spelling,
        # but only exact UBS AlternateLemmas in NFC are evidence.
        en[0]["AlternateLemmas"]=fr[0]["AlternateLemmas"]=["Ἰερουσαλημ"]
        self.assertNotEqual(MOD["nfc"]("Ἰερουσαλήμ"),
                            MOD["nfc"]("Ἰερουσαλημ"))
        out=MOD["audit"](report,en,fr)
        self.assertEqual(out["source_evidence_counts"],
                         {"not_in_original_ubs_alternate_lemmas":456})
        self.assertEqual(out["new_source_word_lexical_headwords_approved"],0)


if __name__=="__main__":unittest.main()
