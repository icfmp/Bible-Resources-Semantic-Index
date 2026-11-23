"""The earlier Agag, Saul's king, and Esther's Agagites are not one actor."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rec(kind,name):
    return json.loads((ROOT/"data"/"entities"/kind/(name+".json")).read_text(encoding="utf-8"))
class AgagWitnessSeparation(unittest.TestCase):
    def test_early_king_different_from_sauls_king(self):
        balaam=rec("people","Agag")
        saul=rec("people","Agag.2")
        self.assertEqual(balaam["references"],["04024007"])
        self.assertNotIn("04024007",saul["key_references"])
        self.assertIn("09015032",saul["references"])
        self.assertEqual(saul["localizations"]["eng"]["preferred_label"],
                         "Agag (king opposed by Saul)")
        self.assertNotIn("Agagite",saul["localizations"]["eng"].get("alternate_labels",[]))
    def test_esther_uses_descendant_demonym_not_king_direct_actor(self):
        saul=rec("people","Agag.2")
        people=rec("groups","Agag")
        for verse in ("17003001","17003010","17008003","17008005","17009024"):
            self.assertNotIn(verse,saul["references"])
            self.assertIn(verse,people["references"])
        self.assertFalse(any(w.startswith("o17")
                             for group in saul["explicit_instances"]["wlc"]
                             for w in group))
        self.assertEqual(len(people["explicit_instances"]["wlc"]),5)
        receipts=[x for x in saul["bsi"]["editorial_field_changes"]
                  if x["action"]=="separate_sauls_agag_from_earlier_or_descendant_agagites"]
        self.assertEqual(len(receipts),1)
        self.assertEqual(len(receipts[0]["removed_original_word_groups"]["wlc"]),5)
        self.assertEqual(len(saul["bsi"]["source_sha256"]),64)
if __name__=="__main__":
    unittest.main()
