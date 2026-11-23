"""Proven explicit zoological/object source terms, without inferred word IDs."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={"fauna/Bird":(2,2),"realia/Door":(2,2),
          "realia/Fishnet":(1,1),"realia/Kiln":(1,1),
          "realia/Lot":(2,2),"realia/Rod":(1,2),
          "realia/UnleavenedBread":(2,2)}
class OriginalObjectWordsTest(unittest.TestCase):
    def test_all_added_original_words_have_source_receipt(self):
        for path,(nverse,nword) in EXPECTED.items():
            with self.subTest(path=path):
                row=json.loads((ROOT/"data"/"entities"/(path+".json"))
                               .read_text(encoding="utf-8"))
                receipts=[x for x in row["bsi"]["editorial_field_changes"]
                          if x["action"]=="restore_exact_source_term_in_original_witness"]
                verses=[v for x in receipts for v in x["added_reference_values"]["references"]]
                words=[w for x in receipts for groups in x["added_original_word_groups"].values()
                       for group in groups for w in group]
                self.assertEqual(len(verses),nverse)
                self.assertEqual(len(words),nword)
                self.assertTrue(set(verses).issubset(row["references"]))
                self.assertTrue(set(verses).issubset(row["key_references"]))
                self.assertTrue(all(w[1:9] in verses for w in words))
                self.assertTrue(all(x["reason"] and x["evidence"] for x in receipts))
                self.assertEqual(len(row["bsi"]["source_sha256"]),64)
                self.assertEqual(row["bsi"]["review_status"],
                                 "editorially_reviewed" if path in {"fauna/Bird","realia/Rod"} else "source_unreviewed")
                if path == "realia/Rod":
                    corrections=[x for x in row["bsi"]["editorial_field_changes"]
                                 if x["action"]=="adjudicate_final_source_key_mismatch"]
                    self.assertEqual(len(corrections),1)
                    before=corrections[0]["replaced_field_values"]["before"]["key_references"]
                    after=corrections[0]["replaced_field_values"]["after"]["key_references"]
                    self.assertIn("66012009",before)
                    self.assertNotIn("66012009",after)
                    self.assertIn("66012005",after)
                    self.assertTrue(corrections[0]["reason"] and corrections[0]["evidence"])
                if path == "fauna/Bird":
                    self.assertTrue(any(x["action"] == "restore_independently_pinned_exact_direct_mention"
                                        for x in row["bsi"]["editorial_field_changes"]))
if __name__=="__main__":
    unittest.main()
