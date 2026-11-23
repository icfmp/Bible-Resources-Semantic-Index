"""Regression and negative tests for genuinely resolved source-key identity batches."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from validate_source_key_resolution_batches import validate  # noqa: E402

DATA=ROOT/"data"
LEDGER=DATA/"source-key-next-115-resolved.json"
SELECT=DATA/"source-key-next-115-candidates.json"
PREVIOUS=DATA/"source-key-resolved-115.json"
POOL=DATA/"source-key-unresolved-queue.json"


class IndependentSourceKeyBatchTests(unittest.TestCase):
    def _run(self, ledger=LEDGER):
        return validate(DATA,ledger,SELECT,PREVIOUS,POOL)

    def _tamper(self,transform):
        doc=json.loads(LEDGER.read_text(encoding="utf-8"))
        transform(doc)
        with tempfile.TemporaryDirectory() as path:
            tmp=Path(path)/"tampered.json"
            tmp.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(ValueError):
                self._run(tmp)

    def test_115_new_decisions_are_truly_distinct_from_prior_115(self):
        result=self._run()
        self.assertEqual(result["resolved"],115)
        self.assertEqual(result["prior_resolved"],115)
        self.assertEqual(result["corrected"],8)
        self.assertEqual(result["verified_correct"],107)
        self.assertEqual(result["remaining_outstanding_from_snapshot"],128)
        self.assertGreaterEqual(result["distinct_source_witness_words"],100)

    def test_case_duplication_does_not_count_as_completion(self):
        self._tamper(lambda d:d["cases"].append(d["cases"][0]))

    def test_missing_decision_cannot_be_certified(self):
        self._tamper(lambda d:d["cases"].pop())

    def test_triaged_is_not_resolved(self):
        self._tamper(lambda d:d["cases"][0].__setitem__("outcome","reviewed"))

    def test_ambiguity_is_not_resolved(self):
        self._tamper(lambda d:d["cases"][0].__setitem__("outcome","uncertain"))

    def test_fabricated_word_anchoring_does_not_pass(self):
        self._tamper(lambda d:d["cases"][0]["source_evidence"][0]
                     .__setitem__("pinned_witness_word_id","o010010010999"))

    def test_fabricated_neighbor_relation_does_not_pass(self):
        def change(doc):
            x=next(c for c in doc["cases"] if c["source_id"]=="person:Goliath")
            x["source_evidence"][0]["nearby_native_source_word"]=True
        self._tamper(change)

    def test_missing_target_decision_does_not_pass(self):
        self._tamper(lambda d:d["cases"][0]["source_evidence"].pop())

    def test_fake_corrected_status_requires_a_real_receipt(self):
        def change(doc):
            x=next(c for c in doc["cases"] if c["source_id"]=="person:Cornelius")
            x["outcome"]="corrected"
            x["required_receipt_action"]="does_not_exist"
        self._tamper(change)

    def test_no_edit_case_cannot_hide_a_removed_key(self):
        def change(doc):
            x=next(c for c in doc["cases"] if c["source_id"]=="person:Abishua")
            x["outcome"]="verified_correct"
            x.pop("required_receipt_action",None)
        self._tamper(change)

    def test_different_unpinned_edition_fails(self):
        self._tamper(lambda d:d["source_pins"].__setitem__("wlc",
                                                           "new-corpus@floating"))

    def test_wrong_historical_case_provenance_is_rejected(self):
        def change(doc):
            x=next(c for c in doc["cases"] if c["source_id"]=="person:Dan")
            x["target_key_verses"]=["01049019","01049020"]
        self._tamper(change)

    def test_genuine_verse_and_identity_repairs(self):
        def obj(directory,name):
            return json.loads((DATA/"entities"/directory/(name+".json"))
                              .read_text(encoding="utf-8"))
        abishua=obj("people","Abishua")
        ad=obj("people","Adoram")
        sol=obj("people","Solomon")
        cp=obj("places","Capernaum")
        sickle=obj("realia","Sickle")
        dan=obj("people","Dan")
        reuel=obj("people","Reuel.3")
        jair=obj("people","Jair.2")
        for verse in ("10006003","10006004"):
            self.assertNotIn(verse,abishua["key_references"])
        self.assertNotIn("11005014",ad["key_references"])
        self.assertIn("11005028",ad["key_references"])
        self.assertNotIn("11004029",sol["key_references"])
        self.assertIn("11005009",sol["key_references"])
        self.assertNotIn("40001012",cp["key_references"])
        self.assertNotIn("05023025",sickle["key_references"])
        self.assertIn("05023026",sickle["key_references"])
        self.assertNotIn("01049019",dan["key_references"])
        for verse in ("01036011","01036012"):
            self.assertNotIn(verse,reuel["key_references"])
        self.assertNotIn("04027001",jair["key_references"])
        self.assertIn(["o130060350081"],abishua["explicit_instances"]["wlc"])
        self.assertIn(["o110050280132"],ad["explicit_instances"]["wlc"])
        self.assertIn(["o110050090042"],sol["explicit_instances"]["wlc"])
        self.assertIn(["o050230260082"],sickle["explicit_instances"]["wlc"])


if __name__=="__main__":
    unittest.main()
