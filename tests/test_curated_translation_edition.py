"""Synthetic tests: curated LSG verse surface comparison never infers word links."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "audit_curated_translation_edition.py"
spec = importlib.util.spec_from_file_location("brsi_curated_lsg_diagnostic", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CuratedLSGEditionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.curated = self.root / "curated"
        self.upstream = self.root / "upstream"
        self.candidate = self.root / "candidate"
        for d in (self.curated, self.upstream, self.candidate):
            d.mkdir()
        self.xml = self.curated / "source.xml"
        self.xml.write_text("""<?xml version="1.0" encoding="utf-8"?>
        <osis><osisText><div type="book"><chapter osisID="Gen.1">
        <title>Génèse titre</title>
        <verse sID="Gen.1.1"/>Au commencement<note>non biblique</note> Dieu créa.
        <verse eID="Gen.1.1"/>
        </chapter><chapter osisID="Matt.1">
        <title>Un titre à exclure</title>
        <verse osisID="Matt.1.1"><w>Une</w> <w>bonne</w> nouvelle!
        <note><reference>Exod.1.1</reference>Ajouter faux mots</note></verse>
        <verse osisID="Matt.1.2">L'autre verset.</verse>
        </chapter></div></osisText></osis>""", encoding="utf-8")
        (self.curated / "metadata.json").write_text(json.dumps({
            "version": "1.0.2", "sword_id": "BRLSG1910", "versification": "Segond"
        }), encoding="utf-8")
        self.lock = {
            "schema_version": 1, "module_version": "1.0.2", "sword_id": "BRLSG1910",
            "versification": "Segond", "release_tag": "lsg-1.0.2", "revision": "b" * 40,
            "osis_path": "source.xml", "osis_sha256": module.sha256(self.xml),
            "module_metadata_path": "metadata.json",
        }
        (self.upstream / "nt.tsv").write_text(
            "id\ttext\n40001001001\tUne\n40001001002\tbonne\n40001001003\tnouvelle\n"
            "40001002001\tL'autre\n40001002002\tverset\n", encoding="utf-8")
        (self.upstream / "ot.tsv").write_text("id\ttext\n", encoding="utf-8")
        self.manifest = {
            "schema_version": 1, "revision": "a" * 40,
            "groups": [
                {"canon": "nt", "target": "nt_target"},
                {"canon": "ot", "target": "ot_target"},
            ],
            "inputs": [
                {"key": "nt_target", "path": "nt.tsv", "sha256": module.sha256(self.upstream / "nt.tsv")},
                {"key": "ot_target", "path": "ot.tsv", "sha256": module.sha256(self.upstream / "ot.tsv")},
            ],
        }
        self.candidates = {
            "nt": {
                "canon": "nt", "format": "brsi-translation-alignment-candidate",
                "upstream_revision": "a" * 40,
                "coverage": {"records": 5, "problem_target_token_unattested": 0},
                "records": [
                    {"ordinal": i - 1, "source_lookup_ids": [f"n4000100100{i}"],
                     "target_lookup_ids": [f"4000100100{i}"]} for i in range(1, 4)
                ] + [
                    {"ordinal": 2 + i, "source_lookup_ids": [f"n4000100200{i}"],
                     "target_lookup_ids": [f"4000100200{i}"]} for i in range(1, 3)
                ],
            },
            "ot": {
                "canon": "ot", "format": "brsi-translation-alignment-candidate",
                "upstream_revision": "a" * 40,
                "coverage": {"records": 2},
                "records": [
                    {"target_lookup_ids": ["01001001001"]},
                    {"target_lookup_ids": ["01001002001"]},
                ],
            },
        }
        self.receipt = {"upstream_revision": "a" * 40, "publication_approved": False,
                        "candidate_outputs": {}}
        self.write_candidates()

    def write_candidates(self):
        for canon, document in self.candidates.items():
            path = self.candidate / (canon + ".json")
            path.write_text(json.dumps(document), encoding="utf-8")
            self.receipt["candidate_outputs"][canon] = {"sha256": module.sha256(path)}
        (self.candidate / "receipt.json").write_text(json.dumps(self.receipt), encoding="utf-8")

    def compare(self):
        return module.build_report(self.manifest, self.lock, self.upstream,
                                   self.curated, self.candidate)

    def test_real_osis_conventions_and_no_note_or_title_pollution(self):
        verses = module.read_osis(self.xml)
        self.assertEqual(len(verses), 3)
        self.assertIn("Au commencement", verses["01001001"])
        self.assertNotIn("non biblique", verses["01001001"])
        self.assertNotIn("Un titre à exclure", verses["40001001"])
        self.assertNotIn("Ajouter faux mots", verses["40001001"])
        self.assertIn("Une bonne nouvelle!", verses["40001001"])

    def test_full_report_is_nonpublishing_and_keeps_target_ids_uncertified(self):
        report = self.compare()
        self.assertEqual(report["curated_osis_verses"], 3)
        self.assertEqual(report["nt"]["verse_content_comparison"].get(
            "same_alphanumeric_stream", 0), 2)
        self.assertEqual(report["nt"]["diagnostic_word_streams_equal_verses"], 2)
        self.assertEqual(report["nt"]["target_surface_boundary_classes"], {"whole_one_word": 5})
        self.assertEqual(report["nt"]["aligned_attested_target_boundary_classes"], {"whole_one_word": 5})
        self.assertEqual(report["nt"]["original_unattested_target_ids"], 0)
        self.assertEqual(report["nt"]["token_rows"], 5)
        self.assertEqual(report["ot"]["alignment_groups"], 2)
        self.assertEqual(report["ot"]["target_reference_presence"],
                         {"target_verse_absent": 1, "target_verse_present": 1})
        self.assertFalse(report["nt"]["target_token_id_matches_certified"])
        self.assertFalse(report["ot"]["target_token_id_matches_certified"])
        self.assertFalse(report["publication_approved"])
        self.assertFalse(report["editions_proven_identical"])

    def test_classifies_token_split_without_inventing_equivalence(self):
        path = self.upstream / "nt.tsv"
        path.write_text(
            "id\ttext\n40001001001\tU\n40001001002\tnebonne\n"
            "40001001003\tnouvelle\n40001002001\tL'autre\n40001002002\tverset\n",
            encoding="utf-8")
        self.manifest["inputs"][0]["sha256"] = module.sha256(path)
        report = self.compare()
        self.assertEqual(report["nt"]["verse_content_comparison"].get("same_alphanumeric_stream"), 2)
        self.assertEqual(report["nt"]["aligned_attested_target_boundary_classes"], {
            "splits_curated_word_boundary": 2, "whole_one_word": 3
        })
        self.assertEqual(report["nt"]["automatic_missing_token_remaps"], 0)

    def test_mismatched_verse_remains_unaccepted(self):
        path = self.upstream / "nt.tsv"
        path.write_text(path.read_text().replace("bonne", "mauvaise"), encoding="utf-8")
        self.manifest["inputs"][0]["sha256"] = module.sha256(path)
        report = self.compare()
        self.assertEqual(report["nt"]["verse_content_comparison"]["different_alphanumeric_stream"], 1)
        self.assertEqual(report["nt"]["diagnostic_text_mismatch_coordinates"][0]["bcv"], "40001001")
        self.assertEqual(report["nt"]["aligned_attested_target_boundary_classes"]["verse_text_mismatch"], 3)

    def test_adjacent_verse_surface_shift_is_diagnostic_not_a_remap(self):
        path = self.upstream / "nt.tsv"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("nouvelle", "nouvelleL").replace("L'autre", "'autre"),
                        encoding="utf-8")
        self.manifest["inputs"][0]["sha256"] = module.sha256(path)
        report = self.compare()
        self.assertEqual(report["nt"]["verse_content_comparison"]["different_alphanumeric_stream"], 2)
        self.assertEqual(report["nt"]["adjacent_mismatch_verses_with_identical_combined_stream"], 2)
        self.assertEqual(report["nt"]["adjacent_text_mismatch_runs"], [{
            "first_bcv": "40001001", "last_bcv": "40001002",
            "verse_count": 2, "combined_alphanumeric_stream_equal": True,
            "automatic_verse_reassignments": 0
        }])
        self.assertFalse(report["nt"]["target_token_id_matches_certified"])

    def test_own_index_preserves_original_ids_and_reverse_lookup(self):
        import gzip
        output = self.root / "internal-index.json.gz"
        report = module.build_report(self.manifest, self.lock, self.upstream,
                                     self.curated, self.candidate, output)
        receipt = report["private_nt_word_index"]
        self.assertEqual(receipt["coverage"]["surface_word_position_candidate"], 5)
        self.assertFalse(receipt["editorially_approved"])
        self.assertEqual(module.sha256(output), receipt["gzip_sha256"])
        payload = json.loads(gzip.decompress(output.read_bytes()))
        self.assertEqual(payload["status"], "private_nonpublishing_unapproved")
        self.assertEqual(payload["index_owner"], "Bible Resources Semantic Index")
        self.assertEqual(payload["format"], "brsi-curated-translation-word-index-candidate")
        self.assertEqual(payload["by_original_macula_id"]["n40001001001"], [0])
        self.assertEqual(payload["by_curated_word"]["40001001:1"], [0])
        self.assertEqual(payload["rows"][0]["original_macula_ids"], ["n40001001001"])
        self.assertEqual(payload["rows"][0]["original_target_ids"], ["40001001001"])
        self.assertEqual(payload["rows"][0]["curated_diagnostic_word_ordinal"], 1)
        self.assertFalse(payload["rows"][0]["editorially_approved"])

    def test_own_index_retains_unattested_and_crossverse_abstentions(self):
        verses = module.read_osis(self.xml)
        targets, _ = module.read_target_tsv(self.upstream / "nt.tsv")
        candidate = {
            "coverage": {"records": 3},
            "records": [
                {"ordinal": 0, "source_lookup_ids": ["n40001001001"],
                 "target_lookup_ids": ["40001001001"]},
                {"ordinal": 1, "source_lookup_ids": ["n40001001001"],
                 "target_lookup_ids": ["40001001999"]},
                {"ordinal": 2, "source_lookup_ids": ["n40001002001"],
                 "target_lookup_ids": ["40001001002"]},
            ],
        }
        raw, counts = module.build_private_nt_word_index(
            verses, targets, candidate, self.lock, self.manifest["revision"])
        payload = json.loads(raw)
        self.assertEqual(counts["surface_word_position_candidate"], 1)
        self.assertEqual(counts["reason_unattested_target_selector"], 1)
        self.assertEqual(counts["reason_cross_verse_selector"], 1)
        self.assertEqual(payload["rows"][1]["status"], "unresolved")
        self.assertEqual(payload["by_original_macula_id"]["n40001001001"], [0, 1])
        self.assertEqual(payload["by_curated_word"]["40001001:1"], [0])
        self.assertNotIn("40001001:2", payload["by_curated_word"])
        self.assertIsNone(payload["rows"][1]["curated_diagnostic_word_ordinal"])
        self.assertFalse(payload["rows"][2]["editorially_approved"])

    def test_own_index_rejects_output_inside_checked_out_repository(self):
        output = Path.cwd() / "should-not-write-index.json.gz"
        with self.assertRaisesRegex(ValueError, "must not be written in checkout"):
            module.build_report(self.manifest, self.lock, self.upstream,
                                self.curated, self.candidate, output)
        self.assertFalse(output.exists())

    def test_fails_when_authorial_verse_body_changes_behind_pin(self):
        self.xml.write_text("<osis></osis>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "pinned byte witness differs"):
            self.compare()

    def test_fails_when_wrong_curated_version_or_versification(self):
        (self.curated / "metadata.json").write_text(json.dumps({
            "version": "1.0.0", "sword_id": "BRLSG1910", "versification": "Segond"
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "identity/versification mismatch"):
            self.compare()

    def test_reject_curated_metadata_path_escape(self):
        self.lock["module_metadata_path"] = "../../outside.json"
        with self.assertRaisesRegex(ValueError, "unsafe curated module metadata path"):
            self.compare()

    def test_fails_on_tampered_original_french_inventory(self):
        with (self.upstream / "nt.tsv").open("a") as stream:
            stream.write("40001001004\tinventé\n")
        with self.assertRaisesRegex(ValueError, "pinned byte witness differs"):
            self.compare()

    def test_fails_on_tampered_candidate(self):
        self.candidates["ot"]["records"][0]["target_lookup_ids"] = ["01001003001"]
        (self.candidate / "ot.json").write_text(json.dumps(self.candidates["ot"]))
        with self.assertRaisesRegex(ValueError, "candidate differs"):
            self.compare()

    def test_fails_on_missing_or_duplicate_token_ids(self):
        path = self.upstream / "nt.tsv"
        path.write_text("id\ttext\n40001001001\tUn\n40001001001\tDeux\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate original target selector"):
            module.read_target_tsv(path)

    def test_fails_on_unrecognized_source_verse(self):
        self.xml.write_text("<osis><verse osisID='Unknown.1.1'>foo</verse></osis>")
        with self.assertRaisesRegex(ValueError, "unsupported OSIS verse coordinate"):
            module.read_osis(self.xml)

    def test_is_not_fuzzy_translation_normalization(self):
        self.assertEqual(module.character_stream("Dieu créa!"), module.character_stream("DIEU créa"))
        self.assertNotEqual(module.character_stream("Dieu créa"), module.character_stream("Dieu créera"))
        self.assertNotEqual(module.character_stream("côte"), module.character_stream("cote"))
        self.assertEqual(module.word_stream("aujourd’hui"), ["aujourdhui"])

    def test_fails_on_unpaired_source_milestone(self):
        path = self.curated / "unterminated.xml"
        path.write_text("<osis><verse sID='Gen.1.1'/>bonjour</osis>")
        with self.assertRaisesRegex(ValueError, "unterminated OSIS verse"):
            module.read_osis(path)


if __name__ == "__main__":
    unittest.main()
