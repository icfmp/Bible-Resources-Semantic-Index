"""Private two-stage *whole-verse* bilingual inference runner regressions.

All source and model messages in this suite are SYNTHETIC, not Scripture or
human gold. A passing test proves structure and evidence boundaries ONLY.
"""
from __future__ import annotations

import contextlib
import copy
import io
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def import_at(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

runner = import_at("scripts/run_macula_lsg_verse_two_pass_model.py",
                   "brsi_private_two_pass_local_model")
fixtures = import_at("tests/test_macula_lsg_verse_semantic_pilot.py",
                     "brsi_synthetic_verse_pilot_fixtures")


class FakeLocalSemanticModel:
    def __init__(self):
        self.phases = []
        self.prompts = []
        self.mode = "good"

    def __call__(self, messages, *, endpoint, model, max_tokens, timeout):
        self.assert_safe_endpoint = runner.assert_loopback_endpoint(endpoint)
        prompt = json.loads(messages[-1]["content"])
        self.prompts.append(prompt)
        task = prompt["task"]
        sources = [t["original_macula_id"]
                   for t in task["source_tokens_in_original_order"]]
        targets = [t["word_id"]
                   for t in task["exact_authored_french_verse"]["exact_words"]]
        if "frozen_whole_verse_interpretation" not in prompt:
            self.phases.append("first")
            return {
                "source_verse_sense": "This entire synthetic sentence expresses one proposition.",
                "french_verse_sense": "Cette phrase française artificielle présente une proposition.",
                "clauses": [{
                    "original_macula_ids": sources,
                    "french_spans": [{"word_ids": targets}],
                    "clause_sense": "This source clause corresponds to a French proposition.",
                }],
            }
        self.phases.append("second")
        first = prompt["frozen_whole_verse_interpretation"]
        clauses = copy.deepcopy(first["clauses"])
        if self.mode == "change_clause":
            clauses[0]["clause_sense"] = "This clause was rewritten by a second-stage model."
        clause = clauses[0]
        clause["alignments"] = [
            {
                "original_macula_ids": sources[:3],
                "french_spans": [{"word_ids": targets[:3]}],
                "decision": "phrase_span",
                "contextual_reason": "This complete original phrase expresses the initial semantic predicate.",
                "grammatical_function": None,
                "uncertainty_reason": None,
            },
            {
                "original_macula_ids": sources[3:4],
                "french_spans": [],
                "decision": "grammatical_unpaired",
                "contextual_reason": "The original grammatical part functions within the whole clause.",
                "grammatical_function": "article",
                "uncertainty_reason": None,
            },
            {
                "original_macula_ids": sources[4:],
                "french_spans": [{"word_ids": targets[2:]}],
                "decision": "phrase_span",
                "contextual_reason": "The rest of this phrase expresses a contiguous meaning despite overlap.",
                "grammatical_function": None,
                "uncertainty_reason": None,
            },
        ]
        if self.mode == "cross_verse":
            clause["alignments"][0]["french_spans"][0]["word_ids"] = [
                "99099099:1"]
        if self.mode == "invent_source":
            clause["alignments"][0]["original_macula_ids"][0] = "n99099099001"
        if self.mode == "approval":
            clause["alignments"][0]["semantically_approved"] = True
        if self.mode == "forced_unpaired":
            clause["alignments"][1]["french_spans"] = [{"word_ids": targets[:1]}]
        clause["french_only_constructions"] = []
        if self.mode == "unexplained_french":
            clause["alignments"][0]["french_spans"] = [
                {"word_ids": targets[2:3]}]
        if self.mode in {"explained_french", "conflict_french"}:
            clause["alignments"][0]["french_spans"] = [
                {"word_ids": targets[2:3]}]
            clause["french_only_constructions"] = [{
                "word_ids": targets[:2],
                "function": "grammatical_restructuring",
                "contextual_reason":
                    "The target-language grammatical construction requires extra wording.",
            }]
            if self.mode == "conflict_french":
                clause["french_only_constructions"][0]["word_ids"] = targets[2:3]
        return {"clauses": clauses}


class TwoPassWholeVerseModelTests(unittest.TestCase):
    def setUp(self):
        self.dossier = fixtures.fixture()
        self.pilot, self.source_receipt = runner.schema.prepare_pilot(
            self.dossier, dossier_sha="f" * 64, nt_count=3, ot_count=3)
        self.source_sha = "a" * 64
        self.model = FakeLocalSemanticModel()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.checkpoint = Path(self.tmp.name) / "checkpoint.private.json"
        self.endpoint = "http://127.0.0.1:11434/v1/chat/completions"

    def perform(self, *, limit=2):
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            report = runner.run(
                self.pilot, self.source_sha, model="offline-demo-model",
                checkpoint=self.checkpoint, limit=limit,
                endpoint=self.endpoint, completion=self.model)
        return report, capture.getvalue()

    def test_two_calls_per_complete_verse_pass_one_before_span_alignment(self):
        report, logs = self.perform(limit=2)
        self.assertEqual(self.model.phases, ["first", "second"] * 2)
        self.assertEqual(report["analyzed_complete_verses"], 2)
        self.assertTrue(report["two_local_inference_passes_per_completed_verse"])
        self.assertEqual(report["original_parts_with_machine_disposition"], 20)
        self.assertEqual(report["french_words_explained_as_target_only_grammar"], 0)
        self.assertEqual(report["dispositions_by_original_part"],
                         {"grammatical_unpaired": 2, "phrase_span": 18})
        self.assertFalse(report["independent_semantic_accuracy_measured"])
        self.assertFalse(report["publication_authorized"])
        self.assertEqual(report["semantic_links_approved"], 0)
        self.assertEqual(report["human_gold_cases_reviewed"], 0)
        self.assertNotIn("La phrase", logs)
        self.assertNotIn("La phrase", json.dumps(report))
        self.assertNotIn("form-1", json.dumps(report))
        self.assertNotIn("source_tokens_in_original_order", logs)

    def test_model_sees_full_original_and_complete_exact_french_verse(self):
        self.perform(limit=1)
        before, after = self.model.prompts
        self.assertEqual(len(before["task"]["source_tokens_in_original_order"]), 10)
        self.assertEqual(len(before["task"]["exact_authored_french_verse"]["exact_words"]), 6)
        self.assertTrue(before["task"]["exact_authored_french_verse"]["nfc_verse"])
        self.assertNotIn("priority_original_macula_ids", json.dumps(before))
        self.assertNotIn("human_gold", json.dumps(before))
        self.assertNotIn("source_cause", json.dumps(before))
        self.assertEqual(
            before["task"]["source_tokens_in_original_order"],
            after["task"]["source_tokens_in_original_order"])
        self.assertEqual(len(after["frozen_whole_verse_interpretation"]["clauses"]), 1)
        self.assertNotIn("alignments",
                         after["frozen_whole_verse_interpretation"]["clauses"][0])

    def test_pass_two_cannot_rewrite_first_pass(self):
        self.model.mode = "change_clause"
        with self.assertRaisesRegex(ValueError, "rewrote pass 1"):
            self.perform(limit=1)
        self.assertFalse(self.checkpoint.exists())

    def test_invented_cross_verse_french_target_is_rejected(self):
        self.model.mode = "cross_verse"
        with self.assertRaisesRegex(ValueError, "unattested|cross-verse"):
            self.perform(limit=1)
        self.assertFalse(self.checkpoint.exists())

    def test_fabricated_macula_source_identity_is_rejected(self):
        self.model.mode = "invent_source"
        with self.assertRaisesRegex(ValueError, "unattested|cross-verse"):
            self.perform(limit=1)
        self.assertFalse(self.checkpoint.exists())

    def test_forced_french_word_for_unpaired_grammar_is_rejected(self):
        self.model.mode = "forced_unpaired"
        with self.assertRaisesRegex(ValueError, "forced onto French"):
            self.perform(limit=1)
        self.assertFalse(self.checkpoint.exists())

    def test_model_cannot_mark_unreviewed_candidate_as_approved(self):
        self.model.mode = "approval"
        with self.assertRaisesRegex(ValueError, "unsafe fields"):
            self.perform(limit=1)
        self.assertFalse(self.checkpoint.exists())

    def test_resume_preserves_model_and_source_provenance(self):
        self.perform(limit=1)
        previous_bytes = self.checkpoint.read_bytes()
        report, _ = self.perform(limit=3)
        self.assertEqual(report["analyzed_complete_verses"], 3)
        self.assertEqual(self.model.phases, ["first", "second"] * 3)
        self.assertNotEqual(previous_bytes, self.checkpoint.read_bytes())
        state = json.loads(self.checkpoint.read_text())
        self.assertEqual(state["model_name"], "offline-demo-model")
        self.assertEqual(state["private_pilot_gzip_sha256"], self.source_sha)
        self.assertEqual(len(state["per_verse_private_provenance"]), 3)
        self.assertEqual(len(state["results"]), 3)
        with self.assertRaisesRegex(ValueError, "source fingerprint changed"):
            runner.run(self.pilot, "b" * 64,
                       model="offline-demo-model", checkpoint=self.checkpoint,
                       limit=3, endpoint=self.endpoint,
                       completion=self.model)
        with self.assertRaisesRegex(ValueError, "model or original source"):
            runner.run(self.pilot, self.source_sha,
                       model="different-model", checkpoint=self.checkpoint,
                       limit=3, endpoint=self.endpoint,
                       completion=self.model)

    def test_model_checkpoint_is_invalid_after_citation_mutation(self):
        self.perform(limit=1)
        state = json.loads(self.checkpoint.read_text())
        state["results"][0]["clauses"][0]["alignments"][0][
            "original_macula_ids"][0] = "n00000000001"
        self.checkpoint.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "unattested|cross-verse"):
            self.perform(limit=2)

    def test_reverse_target_coverage_detects_unexplained_french_expression(self):
        self.model.mode = "unexplained_french"
        with self.assertRaisesRegex(ValueError, "unexplained"):
            self.perform(limit=1)
        self.assertFalse(self.checkpoint.exists())

    def test_french_only_grammatical_expansion_kept_separate_from_source_link(self):
        self.model.mode = "explained_french"
        report, logs = self.perform(limit=1)
        self.assertEqual(report["french_words_explained_as_target_only_grammar"], 2)
        self.assertEqual(report["semantic_links_approved"], 0)
        self.assertNotIn("contextual_reason", logs)
        state = json.loads(self.checkpoint.read_text())
        self.assertEqual(state["per_verse_private_provenance"][0][
            "french_only_word_count"], 2)
        self.assertEqual(len(state["per_verse_private_provenance"][0][
            "private_french_only_constructions_by_clause"][0]), 1)

    def test_target_only_phrase_cannot_also_claim_original_translation(self):
        self.model.mode = "conflict_french"
        with self.assertRaisesRegex(ValueError, "overlapping/conflicting"):
            self.perform(limit=1)
        self.assertFalse(self.checkpoint.exists())

    def test_refuse_network_egress_and_redirects(self):
        for bad in (
            "https://api.openai.com/v1/chat/completions",
            "http://model.example/v1/chat/completions",
            "http://localhost.evil.com:11434/v1/chat/completions",
            "http://localhost:11434/redirect",
            "http://127.0.0.1:11434/v1/chat/completions?redirect=evil",
            "http://localhost:11434@evil.net/v1/chat/completions",
        ):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    ValueError, "ONLY to loopback"):
                runner.assert_loopback_endpoint(bad)
        self.assertEqual(runner.assert_loopback_endpoint(
            "http://[::1]:11434/v1/chat/completions"),
            "http://[::1]:11434/v1/chat/completions")
        with self.assertRaisesRegex(ValueError, "unsafe redirect"):
            runner.NoRedirect().redirect_request(None, None, 302, "", {}, 
                "https://evil.example/private")

    def test_source_fingerprint_validation_rejects_tampered_private_pilot(self):
        packed = runner.schema.pack_private(self.pilot)
        path = Path(self.tmp.name) / "tasks.gz"
        lock = Path(self.tmp.name) / "frozen.json"
        path.write_bytes(packed)
        lock.write_text(json.dumps({
            "kind": "brsi-whole-verse-semantic-pilot-source-free-receipt",
            "pilot_id": self.pilot["pilot_id"],
            "source_dossier_gzip_sha256": self.pilot["source_dossier_gzip_sha256"],
            "private_pilot_gzip_sha256": runner.digest(packed),
            "private_pilot_gzip_bytes": len(packed),
            "verses": len(self.pilot["tasks"]),
        }))
        pilot, proof = runner.verify_private_pilot(path, lock)
        self.assertEqual(proof, runner.digest(packed))
        self.assertEqual(len(pilot["tasks"]), 6)
        path.write_bytes(b"edited-private-candidate")
        with self.assertRaisesRegex(ValueError, "pinned receipt"):
            runner.verify_private_pilot(path, lock)

    def test_checkpoint_rejects_oversized_limit_and_unverified_model_digest(self):
        with self.assertRaisesRegex(ValueError, "count exceeds"):
            self.perform(limit=7)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            runner.run(self.pilot, self.source_sha,
                       model="demo", model_digest="not-a-digest",
                       checkpoint=self.checkpoint, limit=1,
                       endpoint=self.endpoint, completion=self.model)

    def test_empty_or_noncontextual_first_stage_not_allowed(self):
        def one_bad_call(messages, **kwargs):
            return {"source_verse_sense": "word", "french_verse_sense": "word",
                    "clauses": []}
        with self.assertRaisesRegex(ValueError, "substantive"):
            runner.two_pass_one_verse(self.pilot["tasks"][0],
                model="demo", completion=one_bad_call,
                endpoint=self.endpoint, max_tokens=8192, timeout=60)

if __name__ == "__main__":
    unittest.main()
