"""Apocryphal-only sites and anachronistic Asia Minor are not canonical mentions."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ApocryphalCanonicalScopeTests(unittest.TestCase):
    def test_apocryphal_verse_keys_not_canonically_attested(self):
        for n,v in (("Adasa","78007040"),("Arbela","78009002"),
                    ("Bostra","78005026")):
            with self.subTest(n=n):
                o=json.loads((ROOT/"data"/"entities"/"places"/(n+".json"))
                             .read_text(encoding="utf-8"))
                self.assertEqual(o["key_references"],[v])
                self.assertTrue(o["only_mentioned_in_apocrypha"])
                self.assertFalse(o["mentioned_in_bible"])
                self.assertTrue(o["non_biblical"])
                self.assertEqual(o["references"],[])
                self.assertEqual(o["explicit_instances"],{})
                self.assertEqual(len(o["bsi"]["source_sha256"]),64)
    def test_modern_asia_minor_not_asserted_as_named_nt_place(self):
        o=json.loads((ROOT/"data"/"entities"/"places"/"AsiaMinor.json")
                     .read_text(encoding="utf-8"))
        self.assertFalse(o["only_mentioned_in_apocrypha"])
        self.assertFalse(o["mentioned_in_bible"])
        self.assertTrue(o["non_biblical"])
        self.assertEqual(o["key_references"],["44006009","44016006"])
        self.assertEqual(o["references"],[])
        self.assertEqual(o["explicit_instances"],{})
        edits=[x for x in o["bsi"]["editorial_field_changes"]
               if x["action"]=="correct_apocryphal_vs_canonical_place_scope"]
        self.assertEqual(len(edits),1)
        self.assertEqual(edits[0]["replaced_field_values"]["only_mentioned_in_apocrypha"],
                         {"from":True,"to":False})
        self.assertTrue(edits[0]["evidence"])
if __name__=="__main__":
    unittest.main()
