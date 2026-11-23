"""Review all native key-only pairs without manufacturing direct-name evidence."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_active_key_only_reconciliation import reconcile,load_existing_reviews

class NativeKeyOnlyReconciliationTests(unittest.TestCase):
    def test_complete_current_census_is_disjoint_and_independently_accounted(self):
        report=reconcile(ROOT/"data")
        self.assertEqual(report["source_records_scanned"],5771)
        self.assertEqual(report["key_only_pairs"],462)
        self.assertEqual(report["entities_with_key_only_claims"],264)
        self.assertEqual(report["original_indirect_pair_count"],53)
        self.assertEqual(report["individually_reviewed_unanchored_places"],27)
        self.assertEqual(report["previously_certified_unique_source_identities"],358)
        self.assertEqual(report["counts"]["previously_certified"],125)
        self.assertEqual(sum(report["counts"].values()),report["key_only_pairs"])
        self.assertEqual(len({(c["source_id"],c["verse_id"]) for c in report["cases"]}),
                         report["key_only_pairs"])
        self.assertTrue(all(c["status"]!="lexical_candidate_requires_identity_review"
                            for c in report["cases"]))  # no TSV: never fabricate match

    def test_historical_source_coverage_is_truly_case_specific(self):
        resolved=load_existing_reviews(ROOT/"data")
        self.assertEqual(len(resolved),358)
        report=reconcile(ROOT/"data")
        historic={(x["source_id"],x["verse_id"]) for x in report["cases"]
                  if x["status"]=="previously_certified"}
        self.assertTrue(historic)
        self.assertTrue(all(verse in resolved[sid]["keys"] for sid,verse in historic))
        self.assertNotIn(("person:Paul","44009002"),historic)
        self.assertIn(("deity:Beelzebub","41003022"),
                      {(k,v) for k,val in resolved.items() for v in val["keys"]})

    def test_linguistic_or_historical_cross_reference_is_not_direct_name(self):
        cases={(r["source_id"],r["verse_id"]):r
               for r in reconcile(ROOT/"data")["cases"]}
        self.assertEqual(cases[("place:Nehelam","24029024")]["status"],
                         "place_context_individually_qualified")
        self.assertEqual(cases[("place:SouthGate","13026015")]["status"],
                         "place_context_individually_qualified")
        self.assertEqual(cases[("person:Paul","44009002")]["status"],
                         "indirect_original_word_requires_coreference")

if __name__=="__main__":
    unittest.main()
