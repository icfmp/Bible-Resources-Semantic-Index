"""Native BRSI localization policy must be fail-closed and source-preserving."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brsi_localization_policy",
    ROOT / "scripts" / "localization_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def current_record(path):
    return json.loads((ROOT / "data" / "entities" / path).read_text(encoding="utf-8"))


class LocalizationPolicyTests(unittest.TestCase):
    def test_inherited_hold_blocks_contradictory_descriptions_everywhere(self):
        for path in ("people/Jashar.json", "people/Perez-uzzah.json",
                     "people/Johanan.json", "people/Shallum.5.json"):
            with self.subTest(path=path):
                rec = current_record(path)
                original = copy.deepcopy(rec)
                for language in ("eng", "fra", "spa"):
                    with self.assertRaisesRegex(ValueError, "Unsupported"):
                        policy.reader_field(rec, language, "descriptions")
                self.assertEqual(rec, original)

    def test_language_scoped_hold_does_not_block_unrelated_field(self):
        rec = current_record("places/Gadara.json")
        self.assertIsNone(policy.reader_field(rec, "eng", "alternate_labels"))
        label = policy.reader_field(rec, "fra", "preferred_label")
        self.assertEqual(label["review_status"], "source_unreviewed")
        self.assertEqual(label["source_id"], "place:Gadara")
        self.assertEqual(label["value"], rec["localizations"]["fra"]["preferred_label"])
        sample = {"bsi": {"source_id": "person:Fixture"}, "localizations": {
            "eng": {"alternate_labels": ["Name"]}}}
        aliases = policy.reader_field(sample, "eng", "alternate_labels")
        aliases["value"].append("Modified")
        self.assertEqual(sample["localizations"]["eng"]["alternate_labels"], ["Name"])

    def test_reclassified_person_identity_labels_are_not_served(self):
        for path in ("people/Johanan.json", "people/Perez-uzzah.json"):
            rec = current_record(path)
            for lang in ("eng", "fra"):
                self.assertIsNone(policy.reader_field(rec, lang, "preferred_label"))
            self.assertIsNone(policy.reader_field(rec, "eng", "alternate_labels"))

    def test_unheld_label_is_explicitly_source_unreviewed(self):
        rec = current_record("places/Gadara.json")
        data = policy.reader_field(rec, "eng", "preferred_label")
        self.assertEqual(data["field"], "preferred_label")
        self.assertEqual(data["review_status"], "source_unreviewed")
        self.assertEqual(data["value"], rec["localizations"]["eng"]["preferred_label"])

    def test_unknown_status_selector_or_missing_provenance_fails_closed(self):
        rec = current_record("places/Gadara.json")
        bad = copy.deepcopy(rec)
        bad["bsi"]["inherited_localizations"]["status"] = "approved"
        with self.assertRaisesRegex(ValueError, "review status"):
            policy.reader_field(bad, "eng", "preferred_label")
        bad = copy.deepcopy(rec)
        bad["bsi"]["inherited_localizations"]["fields"] = ["eng.description"]
        with self.assertRaisesRegex(ValueError, "selector"):
            policy.validated_holds(bad)
        bad = copy.deepcopy(rec)
        bad["bsi"]["inherited_localizations"]["source"] = ""
        with self.assertRaisesRegex(ValueError, "provenance"):
            policy.validated_holds(bad)
        bad = copy.deepcopy(rec)
        bad["bsi"]["inherited_localizations"]["fields"] = ["descriptions", "descriptions"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            policy.validated_holds(bad)


    def test_enyclopedic_prose_is_forbidden_even_if_still_present_in_source(self):
        raw = {"bsi": {"source_id": "person:Fixture"}, "localizations": {
            "eng": {"descriptions": [{"description": "Not index content"}]}}}
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            policy.reader_field(raw, "eng", "descriptions")

    def test_unsupported_field_or_locale_never_falls_back(self):
        rec = current_record("places/Gadara.json")
        for field in ("biography", "gender", "source_id"):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Unsupported"):
                policy.reader_field(rec, "eng", field)
        for locale in ("en", "EN", "../", "eng.us"):
            with self.subTest(locale=locale), self.assertRaisesRegex(ValueError, "language"):
                policy.reader_field(rec, locale, "preferred_label")


if __name__ == "__main__":
    unittest.main()
