"""Adversarial audit tests for all native Bible-marked unanchored place claims."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_source_place_attestations import validate

class SourcePlaceAttestationTests(unittest.TestCase):
    def examine(self, docket=None):
        return validate(ROOT / "data", docket or ROOT / "data" / "source-place-attestation-review.json")

    def altered(self, change):
        source = json.loads((ROOT / "data" / "source-place-attestation-review.json").read_text(encoding="utf-8"))
        change(source)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spoof.json"
            path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.examine(path)

    def test_full_current_snapshot_and_real_source_witnesses(self):
        result = self.examine()
        self.assertEqual(result["total"], 27)
        self.assertEqual(result["corrected"], 16)
        self.assertEqual(result["contextual_qualified"], 11)
        self.assertEqual(result["distinct_original_words"], 42)
        self.assertEqual(result["categories"]["derived_tribal_allotment"], 13)
        self.assertEqual(result["categories"]["demonym_inferred_locality"], 5)

    def test_source_fingerprints_unmodified_and_wordless_constructs_preserved(self):
        record=json.loads((ROOT / "data" / "source-place-attestation-review.json").read_text(encoding="utf-8"))
        for case in record["cases"]:
            source_id=case["source_id"]
            entity=json.loads((ROOT / "data" / "entities" / "places" /
                               (source_id.split(":",1)[1]+".json")).read_text(encoding="utf-8"))
            self.assertEqual(entity["bsi"]["source_id"],source_id)
            self.assertFalse(entity["references"])
            self.assertFalse(entity["explicit_instances"])
            self.assertEqual(case["original_key_verses"],entity["key_references"])
            if case["attestation_class"]=="derived_tribal_allotment":
                self.assertEqual(entity["place_types"]["acai"],["tribal territory"])
                self.assertEqual(case["original_key_verses"],[])
            if case["outcome"]=="corrected":
                receipts=[r for r in entity["bsi"]["editorial_field_changes"]
                          if r["action"]==case["required_receipt_action"]]
                self.assertEqual(len(receipts),1)
                self.assertNotEqual(receipts[0]["replaced_field_values"]["before"],
                                    receipts[0]["replaced_field_values"]["after"])

    def test_no_forgotten_place(self):
        self.altered(lambda x: x["cases"].pop())

    def test_duplicate_place_is_rejected(self):
        self.altered(lambda x: x["cases"].append(x["cases"][0].copy()))

    def test_forged_original_word_is_not_accepted(self):
        self.altered(lambda x: x["cases"][0]["exact_pinned_word_witnesses"][0]
                     .__setitem__("word_id", "o999999999999"))

    def test_unproven_place_name_is_not_promoted_to_original_direct_word(self):
        self.altered(lambda x: next(c for c in x["cases"]
                                   if c["source_id"]=="place:Meronoth")
                     .__setitem__("attestation_class","derived_tribal_allotment"))

    def test_tribal_allotment_cannot_claim_extra_source_key(self):
        self.altered(lambda x: next(c for c in x["cases"]
                                   if c["source_id"]=="place:TerritoryOfAsher")
                     .__setitem__("original_key_verses",["06019024"]))

    def test_corrupt_edition_pin_is_blocked(self):
        self.altered(lambda x: x["source_editions"].__setitem__("wlc","incorrect edition"))

    def test_missing_receipt_is_blocked(self):
        self.altered(lambda x: next(c for c in x["cases"]
                                   if c["source_id"]=="place:NorthGate")
                     .__setitem__("required_receipt_action","invented"))

    def test_concealed_weak_source_is_blocked(self):
        self.altered(lambda x: next(c for c in x["cases"]
                                   if c["source_id"]=="place:Nehelam")
                     .__setitem__("qualification","town"))

if __name__ == "__main__":
    unittest.main()
