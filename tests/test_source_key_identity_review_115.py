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
        self.assertEqual(result["reviewed_distinct_entities"], 115)
        self.assertEqual(result["source_record_corrections"], 10)
        self.assertEqual(result["classifications"]["direct_witness_restored"], 6)
        self.assertEqual(result["classifications"]["wrong_identity_keys_removed"], 3)
        self.assertEqual(result["classifications"]["wrong_contextual_key_corrected"], 1)
        self.assertEqual(result["classifications"]["constructed_tribal_territory_no_source_key"], 13)
        self.assertEqual(result["classifications"]["indirect_original_referent"], 32)
        self.assertGreater(result["exact_original_word_evidence"], 40)
        self.assertEqual(result["already_indirect_pinned_word_evidence"], 31)
        # Abram and Abraham are two inherited identity records sharing one
        # grammatical referent word in Genesis 17:4; count unique IDs.

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


    def test_no_source_created_tribal_region_has_fabricated_verse_or_word(self):
        review = json.loads(LEDGER.read_text("utf-8"))
        constructed = [x for x in review["reviews"] if x["classification"]
                       == "constructed_tribal_territory_no_source_key"]
        self.assertEqual(len(constructed), 13)
        for case in constructed:
            with self.subTest(case=case["source_id"]):
                filename = case["source_id"].split(":", 1)[1] + ".json"
                row = json.loads((DATA/"entities"/"places"/filename).read_text("utf-8"))
                self.assertEqual(case["reviewed_key_verses"], [])
                self.assertFalse(row["references"])
                self.assertFalse(row["key_references"])
                self.assertFalse(row["explicit_instances"])
                self.assertIn("place:Israel", row["subregion_of"])

    def test_reviewed_indirect_word_is_existing_source_not_invented(self):
        doc = json.loads(LEDGER.read_text("utf-8"))
        case = next(v for v in doc["reviews"] if v["source_id"] == "person:Gideon")
        self.assertEqual(case["classification"], "indirect_original_referent")
        self.assertEqual(case["existing_indirect_word_links"][0]["word_id"],
                         "o070080310092")
        self._reject_mutation(lambda d: next(v for v in d["reviews"]
                                              if v["source_id"] == "person:Gideon")
                              ["existing_indirect_word_links"][0].__setitem__(
                                  "word_id", "o070080310999"))

    def test_balsam_and_poplar_and_amorites_adjacent_verse_kept_separate(self):
        poplar = json.loads((DATA/"entities"/"flora"/"Poplar.json").read_text("utf-8"))
        amorites = json.loads((DATA/"entities"/"groups"/"Amorites.json").read_text("utf-8"))
        highest = json.loads((DATA/"entities"/"deities"/"Highest.json").read_text("utf-8"))
        self.assertNotIn("10005023", poplar["key_references"])
        self.assertNotIn("13001013", amorites["key_references"])
        self.assertIn("13001014", amorites["references"])
        self.assertIn(["o010140190052", "o010140190061"],
                      highest["explicit_instances"]["wlc"])
        self.assertIn(["o010140200021", "o010140200031"],
                      highest["explicit_instances"]["wlc"])

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
