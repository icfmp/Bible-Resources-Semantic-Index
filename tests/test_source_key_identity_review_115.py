"""Evidence-based identity review never turns a contextual verse into a name."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_source_key_identity_reviews import validate  # noqa: E402

LEDGER = ROOT / "data/source-key-identity-review-115.json"
DATA = ROOT / "data"


class SourceIdentityReviewTests(unittest.TestCase):
    def test_approved_review_count_covers_distinct_source_records(self):
        result = validate(DATA, LEDGER)
        self.assertEqual(result["reviewed_distinct_entities"], 63)
        self.assertEqual(result["source_record_corrections"], 7)
        self.assertEqual(result["classifications"]["direct_witness_restored"], 5)
        self.assertEqual(result["classifications"]["wrong_identity_keys_removed"], 1)
        self.assertEqual(result["classifications"]["wrong_contextual_key_corrected"], 1)
        self.assertGreater(result["exact_original_word_evidence"], 40)

    def _reject_mutation(self, change):
        doc = json.loads(LEDGER.read_text("utf-8"))
        change(doc)
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "review.json"
            file.write_text(json.dumps(doc, ensure_ascii=False), "utf-8")
            with self.assertRaises(ValueError):
                validate(DATA, file)

    def test_duplicate_identity_cannot_inflate_count(self):
        self._reject_mutation(lambda doc: doc["reviews"].append(
            copy.deepcopy(doc["reviews"][0])))

    def test_unrelated_verse_cannot_pass_as_an_audit(self):
        self._reject_mutation(lambda doc: doc["reviews"][0].__setitem__(
            "reviewed_key_verses", ["01001001"]))

    def test_invalid_pinned_edition_cannot_pass(self):
        self._reject_mutation(lambda doc: doc["original_sources"].__setitem__(
            "wlc", "unknown@latest"))

    def test_unverified_word_id_cannot_be_called_direct(self):
        def alter(doc):
            case = next(v for v in doc["reviews"]
                        if v["source_id"] == "person:Artaxerxes")
            case["original_word_evidence"][0]["word_id"] = "o150040070999"
        self._reject_mutation(alter)

    def test_a_real_homonym_disambiguation_not_just_a_label(self):
        old = json.loads((DATA / "entities/people/Dishon.json").read_text("utf-8"))
        young = json.loads((DATA / "entities/people/Dishon.2.json").read_text("utf-8"))
        self.assertNotIn("01036025", old["key_references"])
        self.assertNotIn("13001041", old["key_references"])
        self.assertIn("01036025", young["references"])
        self.assertIn("13001041", young["references"])
        self.assertEqual(old["father"], "person:Seir")
        self.assertEqual(young["father"], "person:Anah.2")

    def test_gederathite_adjacent_verse_fixed_without_inventing_place(self):
        row = json.loads((DATA / "entities/places/Gederah.2.json").read_text("utf-8"))
        self.assertEqual(row["key_references"], ["13012005"])
        self.assertEqual(row["references"], [])
        self.assertEqual(row["explicit_instances"], {})
        self.assertEqual(row["bsi"]["editorial_field_changes"][-1]["action"],
                         "correct_gederathite_contextual_key_by_adjacent_original_verse")

    def test_two_distinct_zalmon_hills_not_silently_conflated(self):
        row = json.loads((DATA / "entities/places/ZalmonMount.json").read_text("utf-8"))
        self.assertEqual(row["references"], ["07009048"])
        self.assertEqual(row["explicit_instances"]["wlc"], [["o070090480041"]])
        self.assertNotIn("19068015", row["references"])
        review = json.loads(LEDGER.read_text("utf-8"))
        case = next(v for v in review["reviews"]
                    if v["source_id"] == "place:ZalmonMount")
        self.assertEqual(case["classification"], "uncertain_not_promoted")


if __name__ == "__main__":
    unittest.main()
