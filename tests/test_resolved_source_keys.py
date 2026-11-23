"""A reviewed or unresolved source-key identity cannot count as resolved.

Guard real original-word evidence, reversibility, native identity and the
closed milestone count without changing ancient texts or source versification.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from validate_resolved_source_keys import validate  # noqa: E402

DATA=ROOT/"data"
LEDGER=DATA/"source-key-resolved-115.json"


class ResolvedSourceKeyMilestoneTests(unittest.TestCase):
    def test_exactly_115_resolved_not_merely_categorized(self):
        result=validate(DATA,LEDGER)
        self.assertEqual(result["distinct_resolved"],115)
        self.assertEqual(result["corrected"],36)
        self.assertEqual(result["verified_correct"],79)
        self.assertGreater(result["pinned_original_words"],100)

    def _invalid(self,mutate):
        document=json.loads(LEDGER.read_text(encoding="utf-8"))
        mutate(document)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"invalid.json"
            path.write_text(json.dumps(document,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(ValueError):
                validate(DATA,path)

    def test_duplicate_cases_cannot_inflate_progress(self):
        self._invalid(lambda d:d["cases"].append(d["cases"][0].copy()))

    def test_reviewed_does_not_mean_resolved(self):
        self._invalid(lambda d:d["cases"][0].__setitem__("outcome","reviewed"))

    def test_uncertainty_cannot_be_rebranded_correct(self):
        self._invalid(lambda d:d["cases"][0].__setitem__("outcome","uncertain"))

    def test_wordless_case_not_certified(self):
        self._invalid(lambda d:d["cases"][0].__setitem__("evidence_word_ids",[]))

    def test_original_word_in_impossible_source_book_not_certified(self):
        self._invalid(lambda d:d["cases"][0].__setitem__("evidence_word_ids",
                                                        ["o990010010999"]))

    def test_unknown_source_edition_cannot_pass(self):
        self._invalid(lambda d:d["pin"].__setitem__("wlc","floating@latest"))

    def test_corrected_case_needs_actual_reversible_receipt(self):
        def mutate(d):
            x=next(c for c in d["cases"] if c["source_id"]=="person:Medan")
            x["required_action"]="did_not_actually_change_anything"
        self._invalid(mutate)

    def test_13_tribal_territories_have_genuine_allotment_not_fabricated_name(self):
        cases=json.loads(LEDGER.read_text(encoding="utf-8"))["cases"]
        derived=[c for c in cases if c["proof_kind"]=="derived_allotment"]
        self.assertEqual(len(derived),13)
        for case in derived:
            with self.subTest(tribe=case["source_id"]):
                entry=DATA/"entities"/"places"/(case["source_id"].split(":",1)[1]+".json")
                record=json.loads(entry.read_text(encoding="utf-8"))
                self.assertTrue(record["added_entry"])
                self.assertEqual(record["key_references"],[])
                self.assertEqual(record["references"],[])
                self.assertEqual(record["explicit_instances"],{})
                self.assertIn("place:Israel",record["subregion_of"])
                self.assertEqual(case["evidence_word_ids"][0][1:9],
                                 case["proof_territory_allotment"])

    def test_medan_and_madai_distinct_original_geneaologies(self):
        medan=json.loads((DATA/"entities/people/Medan.json").read_text(encoding="utf-8"))
        madai=json.loads((DATA/"entities/people/Madai.json").read_text(encoding="utf-8"))
        medes=json.loads((DATA/"entities/groups/Mede.json").read_text(encoding="utf-8"))
        self.assertEqual(medan["father"],"person:Abraham")
        self.assertEqual(medan["mother"],"person:Keturah")
        self.assertEqual(medan["references"],["01025002","13001032"])
        self.assertEqual(medan["explicit_instances"],
                         {"wlc":[["o010250020081"],["o130010320092"]]})
        self.assertEqual(madai["father"],"person:Japheth")
        self.assertEqual(medes["group_origin"],"person:Madai")
        self.assertIn(["n44002009003"],medes["explicit_instances"]["SBLGNT"])
        self.assertNotIn("Medan",medes["localizations"]["eng"].get("alternate_labels",[]))

    def test_false_verse_and_wrong_denominations_fixed(self):
        heb=json.loads((DATA/"entities/groups/Hebron.json").read_text(encoding="utf-8"))
        gilead=json.loads((DATA/"entities/groups/Gilead.json").read_text(encoding="utf-8"))
        saw=json.loads((DATA/"entities/realia/Saw.json").read_text(encoding="utf-8"))
        coin=json.loads((DATA/"entities/realia/Two-drachmaPiece.json").read_text(encoding="utf-8"))
        self.assertIn("04026058",heb["key_references"])
        self.assertNotIn("04027058",heb["key_references"])
        self.assertIn("07010003",gilead["key_references"])
        self.assertNotIn("07010030",gilead["key_references"])
        self.assertIn("10012031",saw["key_references"])
        self.assertNotIn("10020031",saw["key_references"])
        self.assertNotIn("40022020",coin["key_references"])
        self.assertNotIn("41012016",coin["key_references"])
        self.assertIn("40017024",coin["references"])


if __name__=="__main__":
    unittest.main()
