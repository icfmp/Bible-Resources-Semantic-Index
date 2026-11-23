"""Source-specific regression guards for final theological and geographical corrections."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/"data"/"entities"

def entity(kind,name):
    return json.loads((ROOT/kind/(name+".json")).read_text(encoding="utf-8"))

class FinalLexicalIdentityTests(unittest.TestCase):
    def test_joel_edition_numbering_and_exact_hebrew_spirit(self):
        row=entity("deities","HolySpirit")
        self.assertIn("29003001",row["key_references"])
        self.assertNotIn("29002028",row["key_references"])
        self.assertIn("01001002",row["key_references"])
        self.assertIn(["o010010020092"],row["explicit_instances"]["wlc"])
        self.assertIn(["o290030010061"],row["explicit_instances"]["wlc"])
        self.assertIn("29003001",row["references"])
        self.assertIn("01001002",row["references"])
        receipts=[x for x in row["bsi"]["editorial_field_changes"]
                  if x["action"]=="repair_hebrew_spirit_source_anchors_and_joel_versification"]
        self.assertEqual(len(receipts),1)
        before,after=[receipts[0]["replaced_field_values"][t] for t in ("before","after")]
        self.assertNotIn("wlc",before["explicit_instances"])
        self.assertEqual(after["explicit_instances"],row["explicit_instances"])
        self.assertIn("29002028",before["key_references"])

    def test_pul_name_not_lud(self):
        pul=entity("places","Pul")
        put=entity("places","Put")
        self.assertEqual(pul["localizations"]["eng"]["preferred_label"],"Pul")
        self.assertEqual(put["localizations"]["eng"]["preferred_label"],"Put")
        self.assertIn(["o230660190101"],pul["explicit_instances"]["wlc"])
        self.assertNotIn("o230660190112",sum(pul["explicit_instances"]["wlc"],[]))
        self.assertEqual(pul["bsi"]["source_id"],"place:Pul")
        receipt=next(x for x in pul["bsi"]["editorial_field_changes"]
                     if x["action"]=="disambiguate_pul_from_lud_source_label")
        self.assertEqual(receipt["replaced_field_values"]["before"]["preferred_label"],"Lud")
        self.assertEqual(receipt["replaced_field_values"]["after"]["preferred_label"],"Pul")
        self.assertEqual(pul["bsi"]["canonical_id"],"place:Put")

    def test_brick_mold_not_in_generic_brick_narratives(self):
        row=entity("realia","BrickMold")
        self.assertNotIn("01011003",row["key_references"])
        self.assertNotIn("02005007",row["key_references"])
        self.assertIn("10012031",row["key_references"])
        self.assertIn("34003014",row["key_references"])
        self.assertIn(["o340030140121"],row["explicit_instances"]["wlc"])
        receipts=[x for x in row["bsi"]["editorial_field_changes"]
                  if x["action"]=="adjudicate_final_source_key_mismatch"]
        self.assertEqual(len(receipts),1)
        self.assertIn("01011003",receipts[0]["replaced_field_values"]["before"]["key_references"])
        self.assertNotIn("01011003",receipts[0]["replaced_field_values"]["after"]["key_references"])

if __name__=="__main__":
    unittest.main()
