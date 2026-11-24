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

    def test_unique_exact_surface_recovers_word_despite_reordered_source_tokens(self):
        original = [
            ("40001001001", "Jean"),
            ("40001001002", "Pierre"),
            ("40001001003", "Paul"),
        ]
        authored = [("Pierre", 0, 6), ("Jean", 7, 11), ("Paul", 12, 16)]
        result = tool.locate_aquifer_words_with_proof(original, authored)
        self.assertEqual(result, {
            0: (1, "unique_exact_surface_without_order_proof"),
            1: (0, "unique_exact_surface_without_order_proof"),
            2: (2, "forced_ordered_exact_word"),
        })
        self.assertEqual([authored[result[i][0]][0] for i in range(3)],
                         ["Jean", "Pierre", "Paul"])

    def test_unique_original_and_curated_trigram_recovers_repeated_word(self):
        # Global word order differs between source edition and authored
        # edition, but both exact three-word phrases are unique in each.
        original = ["Alpha", "Dieu", "parla", "Béthel", "Dieu", "répondit"]
        authored = ["Béthel", "Dieu", "répondit", "Alpha", "Dieu", "parla"]
        tokens = [("40001001" + str(i + 1).zfill(3), word)
                  for i, word in enumerate(original)]
        spans = [(word, i * 20, i * 20 + len(word))
                 for i, word in enumerate(authored)]
        word_matches = tool.locate_aquifer_words_with_proof(tokens, spans)
        self.assertEqual(word_matches[1], (
            4, "unique_exact_contiguous_original_target_trigram"))
        self.assertEqual(word_matches[4], (
            1, "unique_exact_contiguous_original_target_trigram"))
        self.assertEqual(
            [authored[word_matches[i][0]] for i in range(len(original))],
            original)

    def test_repeated_word_trigram_refuses_missing_source_target_ordinal(self):
        original = ["Alpha", "Dieu", "parla", "Béthel", "Dieu", "répondit"]
        authored = ["Béthel", "Dieu", "répondit", "Alpha", "Dieu", "parla"]
        # The first source phrase joins words around an unknown/missing
        # original target token. No positional assumption may bridge it.
        tokens = [("40001001" + str(i + 1 + (i >= 1)).zfill(3), word)
                  for i, word in enumerate(original)]
        spans = [(word, i * 20, i * 20 + len(word))
                 for i, word in enumerate(authored)]
        matches = tool.locate_aquifer_words_with_proof(tokens, spans)
        self.assertNotIn(1, matches)
        self.assertEqual(matches[4][1],
                         "unique_exact_contiguous_original_target_trigram")

    def test_repeated_trigram_cannot_override_any_stronger_word_location(self):
        originals = [("40001001001", "Dieu"),
                     ("40001001002", "parla"),
                     ("40001001003", "Dieu")]
        authored = [("Dieu", 0, 4), ("parla", 5, 10), ("Dieu", 11, 15)]
        existing = {1: (0, "forced_ordered_exact_word")}
        self.assertEqual(tool.contiguous_original_target_trigrams(
            originals, authored, existing), {})
        self.assertEqual(tool.contiguous_original_target_trigrams(
            originals, authored, {}), {
                0: (0, "unique_exact_contiguous_original_target_trigram"),
                1: (1, "unique_exact_contiguous_original_target_trigram"),
                2: (2, "unique_exact_contiguous_original_target_trigram"),
            })
        self.assertEqual(tool.contiguous_original_target_trigrams(
            [("40001001001", "A"), ("40001001003", "X"),
             ("40001001004", "B")],
            [("A", 0, 1), ("X", 2, 3), ("B", 4, 5)], {}), {})

    def test_unique_surface_fallback_never_guesses_repeated_words(self):
        self.assertEqual(tool.locate_aquifer_words_with_proof(
            [("40001001001", "Dieu")],
            [("Dieu", 0, 4), ("Dieu", 5, 9)]), {})
        self.assertEqual(tool.locate_aquifer_words_with_proof(
            [("40001001001", "Dieu"), ("40001001002", "Dieu")],
            [("Dieu", 0, 4)]), {})
        self.assertEqual(tool.locate_aquifer_words_with_proof(
            [("40001001001", "Dieu")],
            [("dieu", 0, 4)]), {})
        self.assertEqual(tool.locate_aquifer_words_with_proof(
            [("40001001001", "Dieu")],
            [("Dien", 0, 4)]), {})

    def test_located_word_witness_preserves_original_target_id_and_hash(self):
        raw, _ = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40)
        doc = json.loads(raw)
        proof = doc["rows"][0]["aquifer_source_word_location_proofs"][0]
        self.assertEqual(proof["aquifer_target_id"], "01001001001")
        self.assertEqual(proof["word_id"], "01001001:1")
        self.assertEqual(proof["location_proof"], "forced_ordered_exact_word")
        import hashlib
        self.assertEqual(proof["word_sha256"],
                         hashlib.sha256(b"Au").hexdigest())
        self.assertFalse(doc["rows"][0]["linguistically_reviewed_by_brsi"])

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

    def test_unlinked_source_explicitly_non_equivalent_is_not_a_missing_word_guess(self):
        self.aquifer_doc["groups"][0]["meta"]["nonEquivalent"]["source"] = [
            "010010010099|אֵת"]
        self.save()
        raw, counters = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40)
        data = json.loads(raw)
        self.assertEqual(
            data["unlinked_cause_by_original_macula_id"]["o010010010099"],
            "aquifer_explicit_non_equivalent_source")
        self.assertEqual(
            data["unlinked_source_cause_counts"]["ot"]["aquifer_explicit_non_equivalent_source"], 1)
        self.assertEqual(
            data["unlinked_source_diagnostics"]["aquifer_non_equivalent_source_unique"], 1)
        self.assertEqual(
            data["source_coverage"]["ot"]["macula_source_ids_without_word_evidence"], 1)
        self.assertEqual(
            counters["unlinked_source_cause_counts"]["ot"]["aquifer_explicit_non_equivalent_source"], 1)
        self.assertEqual(data["rows"][1]["word_ids"], [])
        self.assertFalse(data["rows"][1]["linguistically_reviewed_by_brsi"])

    def test_unlinked_subpart_with_attested_sibling_is_not_silently_mapped(self):
        doc = json.loads((self.candidates / "ot.json").read_text(encoding="utf-8"))
        doc["records"].append({
            "ordinal": 3, "source_lookup_ids": ["o010010010012"],
            "target_lookup_ids": ["01001001998"],
        })
        doc["coverage"]["records"] = 4
        (self.candidates / "ot.json").write_text(json.dumps(doc), encoding="utf-8")
        raw, _ = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40)
        data = json.loads(raw)
        self.assertEqual(
            data["unlinked_cause_by_original_macula_id"]["o010010010012"],
            "other_part_of_same_original_word_has_link")
        self.assertEqual(data["rows"][3]["word_ids"], [])
        self.assertEqual(data["source_coverage"]["ot"]["macula_source_ids_without_word_evidence"], 2)
        self.assertEqual(sum(data["unlinked_source_cause_counts"]["ot"].values()), 2)

    def test_alignment_source_whose_target_was_not_located_remains_unresolved(self):
        self.aquifer_doc["groups"][0]["records"].append({
            "source": ["010010010099|אֵת"],
            "target": ["01001001098|Introuvable"],
        })
        self.save()
        raw, _ = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40)
        data = json.loads(raw)
        self.assertEqual(
            data["unlinked_cause_by_original_macula_id"]["o010010010099"],
            "aquifer_record_source_with_no_uniquely_located_french_word")
        self.assertEqual(data["rows"][1]["word_ids"], [])
        self.assertEqual(sum(data["unlinked_source_cause_counts"]["ot"].values()), 1)
        self.assertEqual(
            data["unlocated_french_target_cause_by_original_macula_id"]["o010010010099"],
            "exact_french_word_absent_from_curated_verse")
        self.assertEqual(
            data["unlocated_french_target_cause_counts"]["ot"],
            {"exact_french_word_absent_from_curated_verse": 1})

    def test_original_repeated_french_target_without_unique_position_remains_unmapped(self):
        self.aquifer_doc["groups"][0]["records"].append({
            "source": ["010010010099|אֵת"],
            "target": ["01001001099|Au"],
        })
        self.save()
        raw, _ = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40)
        doc = json.loads(raw)
        self.assertEqual(doc["rows"][1]["word_ids"], [])
        self.assertEqual(
            doc["unlocated_french_target_cause_by_original_macula_id"]["o010010010099"],
            "repeated_exact_word_surface_not_uniquely_locatable")
        self.assertEqual(
            doc["unlocated_french_target_cause_counts"]["ot"],
            {"repeated_exact_word_surface_not_uniquely_locatable": 1})

    def test_aquifer_source_alignment_without_french_target_remains_unmapped(self):
        self.aquifer_doc["groups"][0]["records"].append({
            "source": ["010010010099|אֵת"],
            "target": [],
        })
        self.save()
        raw, _ = tool.build_corroborated_index(
            self.aquifer, self.candidates, self.osis, self.lock,
            "a" * 40, "b" * 40)
        doc = json.loads(raw)
        self.assertEqual(doc["rows"][1]["word_ids"], [])
        self.assertEqual(
            doc["unlocated_french_target_cause_by_original_macula_id"]["o010010010099"],
            "aquifer_source_record_without_target_token")

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
