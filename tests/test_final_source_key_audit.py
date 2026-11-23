"""Regression suite: a review docket is not completion of its unresolved cases."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from validate_final_source_key_audit import validate  # noqa: E402

class FinalAuditDecisionsTests(unittest.TestCase):
    def evaluate(self,path=None):
        return validate(ROOT/"data",path or ROOT/"data"/"source-key-final-128-review.json")

    def mutate(self,transform):
        d=json.loads((ROOT/"data"/"source-key-final-128-review.json").read_text(encoding="utf-8"))
        transform(d)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"mutated.json"
            path.write_text(json.dumps(d,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(ValueError):
                self.evaluate(path)

    def test_full_128_selection_distinct_from_prior_230(self):
        x=self.evaluate()
        self.assertEqual(x["total"],128)
        self.assertEqual(x["corrected"],44)
        self.assertEqual(x["verified_correct"],69)
        self.assertEqual(x["secondary_verified"],3)
        self.assertEqual(x["unresolved"],12)
        self.assertEqual(x["prior_resolved"],230)
        self.assertEqual(x["remaining_unresolved"],12)
        self.assertGreater(x["distinct_witness_word_ids"],0)  # exact IDs tested against pinned TSVs by CI

    def test_no_unreviewed_case_can_claim_correction(self):
        def change(d):
            x=next(z for z in d["cases"] if z["source_id"]=="place:Misgab.1")
            x["outcome"]="corrected"
            x["required_receipt_action"]="fabricated"
        self.mutate(change)

    def test_corrupted_exact_target_excerpt_fails_with_pins_or_bad_provenance(self):
        self.mutate(lambda d:d["source_editions"].__setitem__("wlc","unlocked"))

    def test_missing_disposition_fails(self):
        self.mutate(lambda d:d["cases"].pop())

    def test_wrong_selection_fails(self):
        self.mutate(lambda d:d["cases"][0].__setitem__("original_key_verses",["01001001"]))

    def test_undocumented_secondary_identity_cannot_pass(self):
        def change(d):
            z=next(x for x in d["cases"] if x["source_id"]=="place:Adasa")
            z["secondary_source"]["url"]=""
        self.mutate(change)

    def test_wrong_original_word_id_fails(self):
        def change(d):
            z=next(x for x in d["cases"] if x["nearby_existing_word_anchors"])
            z["nearby_existing_word_anchors"][0]["word_id"]="o010010010999"
        self.mutate(change)

    def test_edited_record_does_not_lose_its_receipt(self):
        def change(d):
            z=next(x for x in d["cases"] if x["source_id"]=="person:Javan")
            z["required_receipt_action"]="not_a_genuine_source_edit"
        self.mutate(change)

    def test_unresolved_is_not_reported_as_resolved(self):
        doc=json.loads((ROOT/"data"/"source-key-final-128-review.json").read_text(encoding="utf-8"))
        self.assertTrue(all(r["outcome"]!="verified_correct" for r in doc["cases"]
                            if r["source_id"] in {"place:Ai","place:Misgab.1","deity:Beelzebub"}))

if __name__=="__main__":
    unittest.main()
