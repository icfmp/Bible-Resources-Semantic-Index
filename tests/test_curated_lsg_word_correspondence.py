"""Synthetic integrity tests: no guessed MACULA or French word correspondence."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "owned_aquifer", ROOT / "scripts" / "build_curated_lsg_word_correspondence.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class LSGOriginalWordWitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.aquifer = self.root / "aquifer"
        self.group = self.aquifer / "fra" / "alignments" / "json"
        self.group.mkdir(parents=True)
        self.candidates = self.root / "original"
        self.candidates.mkdir()
        self.osis = self.root / "original.xml"
        self.osis.write_text('''<osis><osisText><div><chapter osisID="Gen.1">
            <verse osisID="Gen.1.1">Au commencement, Dieu créa la terre.</verse>
            <verse osisID="Gen.1.2">Au commencement, l'eau est profonde.</verse>
            </chapter></div></osisText></osis>''', encoding="utf-8")
        self.lock = {"release_tag": "lsg-1.0.2", "osis_sha256": tool.ed.sha256(self.osis)}
        original = {
            "canon": "ot",
            "upstream_revision": "a" * 40,
            "coverage": {"records": 3},
            "records": [
                {"ordinal": 0, "source_lookup_ids": ["o010010010011"],
                 "target_lookup_ids": ["01001001001"]},
                {"ordinal": 1, "source_lookup_ids": ["o010010010099"],
                 "target_lookup_ids": ["01001001099"]},
                {"ordinal": 2, "source_lookup_ids": ["o010010020011"],
                 "target_lookup_ids": ["01001002099"]},
            ],
        }
        (self.candidates / "ot.json").write_text(json.dumps(original), encoding="utf-8")
        (self.candidates / "nt.json").write_text(json.dumps({
            "canon": "nt", "upstream_revision": "a" * 40,
            "coverage": {"records": 0}, "records": []
        }), encoding="utf-8")
        self.aquifer_doc = {
            "format": "alignment",
            "version": "0.4",
            "groups": [{
                "type": "translation",
                "documents": [{"docid": "WLCM"}, {"docid": "LSG"}],
                "meta": {"nonEquivalent": {"target": [
                    "01001001002|commencement", "01001001003|Dieu",
                    "01001001004|créa", "01001001006|terre",
                    "01001002001|Au", "01001002002|commencement",
                    "01001002003|l'eau", "01001002004|est",
                    "01001002005|profonde"
                ]}},
                "records": [
                    {"source": ["010010010011|בְּ"],
                     "target": ["01001001001|Au"]},
                    {"source": ["010010010021|בָּרָא"],
                     "target": ["01001001005|la"]},
                    {"source": ["010010020011|וְ"],
                     "target": ["01001002005|profonde"]},
                ]
            }]
        }
        self.save()

    def save(self):
        (self.group / "01-001.alignment.json").write_text(
            json.dumps(self.aquifer_doc, ensure_ascii=False), encoding="utf-8")

    def test_duplicate_subsequence_word_not_invented(self):
        self.assertEqual(tool.unique_ordered_exact_locations(
            ["Dieu"], ["Dieu", "Dieu"]), {})
        self.assertEqual(tool.unique_ordered_exact_locations(
            ["le", "mot"], ["le", "grand", "mot"]), {0: 0, 1: 2})
        self.assertEqual(tool.unique_ordered_exact_locations(
            ["Dieu", "Dieu"], ["Dieu", "Dieu"]), {0: 0, 1: 1})
        self.assertEqual(tool.unique_ordered_exact_locations(
            ["Dieu", "autre"], ["Dieu", "mot"]), {0: 0})

    def test_independent_word_witness_retains_original_source_and_target_ids(self):
        raw, counters = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40)
        doc = json.loads(raw)
        self.assertEqual(doc["original_group_counts"], {"ot": 3, "nt": 0})
        self.assertEqual(len(doc["rows"]), 3)
        self.assertEqual(doc["rows"][0]["original_macula_ids"], ["o010010010011"])
        self.assertEqual(doc["rows"][0]["original_clear_bible_target_ids"], ["01001001001"])
        self.assertEqual(doc["rows"][0]["word_ids"], ["01001001:1"])
        self.assertEqual(doc["rows"][0]["status"], "aquifer_source_word_witness_numeric_coincidence")
        self.assertEqual(doc["by_lsg_word"]["01001001:1"], [0])
        self.assertEqual(doc["rows"][1]["original_clear_bible_target_ids"], ["01001001099"])
        self.assertEqual(doc["rows"][1]["status"], "unresolved_no_source_word_witness")
        self.assertEqual(doc["rows"][2]["status"], "aquifer_source_word_witness")
        self.assertEqual(doc["rows"][2]["word_ids"], ["01001002:5"])
        self.assertEqual(doc["rows"][2]["linguistically_reviewed_by_brsi"], False)
        self.assertEqual(counters["original_group_counts"], {"ot": 3, "nt": 0})

    def test_direct_clear_bible_nt_word_wins_over_incompatible_aquifer_source_alignment(self):
        import gzip
        old = self.osis.read_text(encoding="utf-8")
        self.osis.write_text(old.replace("</osisText>",
            '<div><chapter osisID="Matt.1"><verse osisID="Matt.1.1">'
            'Un mot bon</verse></chapter></div></osisText>'),
            encoding="utf-8")
        self.lock["osis_sha256"] = tool.ed.sha256(self.osis)
        (self.candidates / "nt.json").write_text(json.dumps({
            "canon": "nt", "upstream_revision": "a" * 40,
            "coverage": {"records": 1},
            "records": [{"ordinal": 0,
                         "source_lookup_ids": ["n40001001001"],
                         "target_lookup_ids": ["40001001001"]}],
        }), encoding="utf-8")
        nt_doc = {
            "format": "alignment", "version": "0.4",
            "groups": [{"type": "translation",
                        "documents": [{"docid": "SBLGNT"}, {"docid": "LSG"}],
                        "meta": {"nonEquivalent": {
                            "target": ["40001001001|Un", "40001001002|mot"]}},
                        "records": [{"source": ["40001001001|βίβλος"],
                                     "target": ["40001001003|bon"]}]}],
        }
        (self.group / "40-001.alignment.json").write_text(
            json.dumps(nt_doc, ensure_ascii=False), encoding="utf-8")
        gold = self.root / "gold-nt.json.gz"
        gold.write_bytes(gzip.compress(json.dumps({
            "format": "brsi-curated-translation-word-index-candidate",
            "source_alignment_revision": "a" * 40,
            "curated_osis_sha256": self.lock["osis_sha256"],
            "rows": [{
                "original_macula_ids": ["n40001001001"],
                "original_target_ids": ["40001001001"],
                "status": "surface_word_position_candidate",
                "curated_bcv": "40001001",
                "curated_diagnostic_word_ordinal": 1,
            }],
        }).encode()))
        raw, _ = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40, gold_nt_index=gold)
        doc = json.loads(raw)
        row = doc["rows"][0]
        self.assertEqual(row["status"], "clear_bible_direct_word_aquifer_disagree")
        self.assertEqual(row["word_ids"], ["40001001:1"])
        self.assertEqual(row["aquifer_source_word_witness_ids"], ["40001001:3"])
        self.assertEqual(row["original_clear_bible_target_ids"], ["40001001001"])
        self.assertFalse(row["target_selector_numeric_equivalence_proven"])

    def test_new_and_unlinked_macula_ids_keep_full_source_inventory(self):
        extra = self.aquifer_doc["groups"][0]["records"]
        extra.append({"source": ["010010010031|וְ"],
                      "target": ["01001001004|créa"]})
        self.save()
        original = self.root / "clear"
        original.mkdir()
        nt_tsv = original / "nt.tsv"
        ot_tsv = original / "ot.tsv"
        nt_tsv.write_text("id\n", encoding="utf-8")
        ot_tsv.write_text("id\n010010010011\n010010010099\n"
                          "010010020011\n010010010031\n010010010041\n",
                          encoding="utf-8")
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({
            "revision": "a" * 40,
            "inputs": [
                {"key": "nt_source", "path": "nt.tsv",
                 "sha256": tool.ed.sha256(nt_tsv)},
                {"key": "ot_source", "path": "ot.tsv",
                 "sha256": tool.ed.sha256(ot_tsv)},
            ],
        }), encoding="utf-8")
        raw, stats = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40, clear_root=original, source_manifest=manifest)
        payload = json.loads(raw)
        self.assertEqual(len(payload["rows"]), 5)
        self.assertEqual(len(payload["by_original_macula_id"]), 5)
        self.assertEqual(stats["supplemental_macula_source_counts"]["ot_added_source_words"], 1)
        self.assertEqual(
            stats["supplemental_macula_source_counts"]["ot_source_tokens_without_word_evidence"], 1)
        self.assertEqual(payload["rows"][-2]["word_ids"], ["01001001:4"])
        self.assertEqual(payload["rows"][-2]["status"], "aquifer_additional_pinned_macula_word")
        self.assertEqual(payload["rows"][-1]["word_ids"], [])
        self.assertEqual(payload["rows"][-1]["status"],
                         "pinned_original_macula_word_without_translation_evidence")

    def test_conflicting_french_surfaces_fail_closed(self):
        self.aquifer_doc["groups"][0]["meta"]["nonEquivalent"]["target"].append(
            "01001001001|Autre")
        self.save()
        with self.assertRaisesRegex(ValueError, "conflicting Aquifer"):
            tool.load_aquifer(self.aquifer, tool.ed.read_osis(self.osis))

    def test_source_edition_mismatch_rejected(self):
        self.aquifer_doc["groups"][0]["documents"][0]["docid"] = "UNTRUSTED"
        self.save()
        with self.assertRaisesRegex(ValueError, "unexpected original/target edition"):
            tool.load_aquifer(self.aquifer, tool.ed.read_osis(self.osis))

    def test_invalid_revision_and_incomplete_original_groups(self):
        with self.assertRaisesRegex(ValueError, "invalid pinned"):
            tool.build_corroborated_index(self.aquifer, self.candidates, self.osis,
                                         self.lock, "branch", "b" * 40)
        path = self.candidates / "ot.json"
        data = json.loads(path.read_text())
        data["coverage"]["records"] = 4
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "census altered"):
            tool.build_corroborated_index(self.aquifer, self.candidates,
                                         self.osis, self.lock, "a" * 40, "b" * 40)


if __name__ == "__main__":
    unittest.main()
