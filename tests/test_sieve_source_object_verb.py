"""A sieve artifact is not an occurrence of the Greek verb 'to sift'."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SieveArtifactWitnessTest(unittest.TestCase):
    def test_real_object_direct_wlc_not_false_greek_action(self):
        x=json.loads((ROOT/"data"/"entities"/"realia"/"Sieve.json")
                     .read_text(encoding="utf-8"))
        self.assertNotIn("42022031",x["key_references"])
        self.assertTrue({"23030028","30009009"}.issubset(x["references"]))
        self.assertNotIn("SBLGNT",x["explicit_instances"])
        self.assertIn(["o300090090132"],x["explicit_instances"]["wlc"])
        for label in ("To Sieve","To Sift","Winnowing"):
            self.assertNotIn(label,x["localizations"]["eng"].get("alternate_labels",[]))
        receipts=[r for r in x["bsi"]["editorial_field_changes"]
                  if r["action"]=="remove_verb_as_physical_sieve_object_claim"]
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]["removed_reference_values"],
                         {"key_references":["42022031"]})
        self.assertEqual(len(x["bsi"]["source_sha256"]),64)
if __name__=="__main__":
    unittest.main()
