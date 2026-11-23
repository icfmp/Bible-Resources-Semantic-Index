#!/usr/bin/env python3
"""Fail-closed original WLC final 26-word source check and 2/24 decisions."""
from __future__ import annotations

import hashlib
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
MOD=runpy.run_path(str(HERE/"build_final_reviewed_candidate.py"))
LEDGER=json.loads((HERE/"v1_final_word_specific_approvals.json").read_text(encoding="utf-8"))


class HebrewFinalReviewedSourceTests(unittest.TestCase):
    def test_two_specific_lexical_approvals_and_twenty_four_abstentions(self):
        self.assertEqual(LEDGER["status"],
            "reviewed_last_source_word_specific_ubs_headword_approvals_not_published")
        self.assertEqual(LEDGER["remaining_source_specific_abstentions"],24)
        self.assertEqual(
            {r["word_id"] for r in LEDGER["approved_word_links"]},
            {"o060190130101","o090170390072"})
        self.assertTrue(LEDGER["policy"]["original_macula_fields_immutable"])
        self.assertFalse(LEDGER["policy"]["contextual_ubs_sense_inferred"])
        self.assertTrue(LEDGER["policy"]["word_id_specific_only"])
        for record in LEDGER["approved_word_links"]:
            self.assertFalse(record["source_text_modified"])
            self.assertFalse(record["contextual_lexical_sense_id_approved"])
            self.assertTrue(record["independent_evidence_url"].startswith("https://"))

    def test_final_builder_reexecutes_original_wlc_and_bilingual_ubs_audit(self):
        # The builder cannot accept a substitute precomputed 26-word JSON
        # report. The full independent source audit must be called first.
        func=MOD["build_from_pinned_sources"]
        with patch.dict(func.__globals__["AUDIT"],{
            "run":lambda *args,**kwargs: (_ for _ in ()).throw(
                ValueError("original WLC source audit required"))}):
            with self.assertRaisesRegex(ValueError,"original WLC source audit required"):
                func({}, {}, {}, {}, {}, [], [], Path("/missing.tsv"), {})

    def test_original_pre_review_index_hash_is_fail_closed(self):
        verify=MOD["verify_frozen_original_index"]
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/"original-index.json"
            file.write_bytes(b'{"original":true}\n')
            original=hashlib.sha256(file.read_bytes()).hexdigest()
            indexed={"editorial_candidate":{"original_index_sha256":original}}
            verify(indexed,file)
            for bad in ("0"*64, "", None):
                with self.subTest(expected=bad),self.assertRaisesRegex(
                        ValueError,"Original UBS Hebrew index SHA-256"):
                    verify({"editorial_candidate":{"original_index_sha256":bad}},file)
            file.write_bytes(b'{"original":false}\n')
            with self.assertRaisesRegex(ValueError,"Original UBS Hebrew index SHA-256"):
                verify(indexed,file)


if __name__=="__main__":
    unittest.main()
