"""Recover only attested named-place source tokens from pinned original editions."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEWED={
    "Gihon.2":("wlc",3,3),
    "Ephron.2":("wlc",1,1),
    "Naarah":("wlc",1,1),
    "Rehob.2":("wlc",1,1),
    "Meribah":("wlc",1,1),
    "Syria":("SBLGNT",3,3),
    "Jokmeam":("wlc",1,1),
    "MountZemaraim":("wlc",1,1),
}

class OriginalPlaceWordVerification(unittest.TestCase):
    def test_eight_recovered_direct_source_places_have_precise_receipts(self):
        for name,(corpus,nverses,nwords) in REVIEWED.items():
            with self.subTest(name=name):
                o=json.loads((ROOT/"data"/"entities"/"places"/(name+".json"))
                             .read_text(encoding="utf-8"))
                matches=[c for c in o["bsi"]["editorial_field_changes"]
                         if c["action"]=="restore_exact_source_named_place_occurrence"]
                self.assertEqual(len(matches),1)
                row=matches[0]
                verses=row["added_reference_values"]["references"]
                self.assertEqual(len(verses),nverses)
                self.assertTrue(set(verses).issubset(o["references"]))
                self.assertTrue(set(verses).issubset(o["key_references"]))
                words=row["added_original_word_groups"][corpus]
                self.assertEqual(sum(len(x) for x in words),nwords)
                self.assertTrue(set(w[1:9] for group in words for w in group)
                                .issubset(verses))
                for group in words:
                    self.assertIn(group,o["explicit_instances"][corpus])
                self.assertEqual(o["bsi"]["review_status"],"source_unreviewed")
                self.assertEqual(len(o["bsi"]["source_sha256"]),64)
                self.assertTrue(row["reason"] and row["evidence"])

if __name__=="__main__":
    unittest.main()
