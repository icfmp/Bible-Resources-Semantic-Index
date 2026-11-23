"""Mail coat, whole armor, ink, pen and writing case are distinct objects."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def item(name):
    return json.loads((ROOT/"data"/"entities"/"realia"/(name+".json")).read_text(encoding="utf-8"))

class ObjectIdentityFalsePositiveTests(unittest.TestCase):
    def test_mail_coat_is_not_complete_armor_from_ephesians(self):
        row=item("CoatOfMail")
        self.assertEqual(row["references"],["09017005","09017038"])
        self.assertNotIn("49006011",row["key_references"])
        self.assertTrue(row["explicit_instances"]["wlc"])
        changes=[c for c in row["bsi"]["editorial_field_changes"]
                 if c["action"]=="remove_false_object_equivalence_reference"]
        self.assertEqual(len(changes),1)
        self.assertEqual(changes[0]["removed_reference_values"],
                         {"key_references":["49006011"]})

    def test_writing_case_is_not_ink_or_a_pen(self):
        row=item("WritingCase")
        self.assertNotIn("64001013",row["key_references"])
        self.assertNotIn("Ink",row["localizations"]["eng"]["alternate_labels"])
        self.assertNotIn("Pen",row["localizations"]["eng"]["alternate_labels"])
        self.assertIn("26009002",row["references"])
        self.assertTrue(row["explicit_instances"]["wlc"])
        changes=[c for c in row["bsi"]["editorial_field_changes"]
                 if c["action"]=="remove_false_object_equivalence_reference"]
        self.assertEqual(len(changes),1)
        self.assertEqual(changes[0]["removed_localization_values"],
                         {"eng":{"alternate_labels":["Ink","Pen"]}})
        self.assertEqual(len(row["bsi"]["source_sha256"]),64)

if __name__=="__main__":
    unittest.main()
