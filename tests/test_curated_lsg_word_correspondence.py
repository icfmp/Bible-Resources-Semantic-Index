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
                {"ordinal": 1, "source_lookup_ids": ["o010010010021"],
                 "target_lookup_ids": ["01001001005"]},
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
        self.assertEqual(doc["rows"][0]["status"], "original_target_and_independent_source_agree")
        self.assertEqual(doc["by_lsg_word"]["01001001:1"], [0])
        self.assertEqual(doc["rows"][1]["original_clear_bible_target_ids"], ["01001001005"])
        self.assertEqual(doc["rows"][1]["status"], "unresolved_no_located_word")
        self.assertEqual(doc["rows"][2]["status"], "independent_aquifer_word_witness_only")
        self.assertEqual(doc["rows"][2]["word_ids"], ["01001002:5"])
        self.assertEqual(doc["rows"][2]["linguistically_reviewed_by_brsi"], False)
        self.assertEqual(counters["original_group_counts"], {"ot": 3, "nt": 0})

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
