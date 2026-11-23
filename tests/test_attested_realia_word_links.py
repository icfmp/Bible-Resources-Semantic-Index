"""Original-language object-source corrections are reversible and anchored."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWED = {
    "Censer":(2,4),
    "Cup":(3,4),
    "Tunic":(2,3),
    "Sword":(2,2),
    "Fishhook":(2,2),
    "Lyre":(1,1),
    "Veil":(1,1),
    "Garland":(1,1),
    "Lamp":(1,1),
    "Footstool":(2,2),
    "Incense":(3,3),
    "Sandal":(2,2),
    "Saw":(1,1),
    "Pool":(2,2),
    "Courtyard":(2,4),
    "Tabernacle":(3,6),
    "Wheel":(3,3),
    "Seal":(1,1),
}

class RealWordRealiaSourceTests(unittest.TestCase):
    def test_all_source_claims_are_exact_word_attested_and_reversible(self):
        self.assertEqual(len(REVIEWED),18)
        for name,(nverses,nwords) in REVIEWED.items():
            with self.subTest(name=name):
                o=json.loads((ROOT/"data"/"entities"/"realia"/(name+".json"))
                             .read_text(encoding="utf-8"))
                receipts=[change for change in
                          o["bsi"]["editorial_field_changes"]
                          if change["action"]=="restore_source_attested_object_word_instances"]
                self.assertEqual(len(receipts),1)
                receipt=receipts[0]
                refs=receipt["added_reference_values"]["references"]
                self.assertEqual(len(refs),nverses)
                self.assertTrue(set(refs).issubset(o["references"]))
                words=receipt["added_original_word_groups"]
                flattened=[w for groups in words.values() for group in groups for w in group]
                self.assertEqual(len(flattened),nwords)
                self.assertEqual(len(set(flattened)),nwords)
                self.assertTrue(set(w[1:9] for w in flattened).issubset(refs))
                for corpus,groups in words.items():
                    self.assertIn(corpus,{"wlc","SBLGNT"})
                    for group in groups:
                        self.assertIn(group,o["explicit_instances"][corpus])
                self.assertTrue(receipt["evidence"])
                self.assertTrue(receipt["reason"])
                self.assertEqual(len(o["bsi"]["source_sha256"]),64)
                self.assertEqual(o["bsi"]["review_status"],
                                 "editorially_reviewed" if name == "Seal" else "source_unreviewed")
                if name == "Seal":
                    self.assertTrue(any(x["action"] == "restore_pinned_lexical_object_term_from_key"
                                        for x in o["bsi"]["editorial_field_changes"]))

if __name__=="__main__":
    unittest.main()
