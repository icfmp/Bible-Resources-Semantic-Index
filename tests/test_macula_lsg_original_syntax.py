"""Prove MACULA source syntax remains structural evidence, never auto links."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_syntax_test", ROOT / "scripts" /
    "audit_macula_lsg_original_syntax.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

OT_PATH = "WLC/lowfat/01-Gen-001-lowfat.xml"
NT_PATH = "SBLGNT/lowfat/24-2john.xml"
OT_IDS = (
    "o010010010011", "o010010010012",
    "o010010010021", "o010010010031",
)
NT_IDS = ("n63001001001", "n63001001002", "n63001001003")

OT_XML = """<chapter id="GEN 1" lang="he">
<sentence><wg class="cl" role="v" rule="S-V-O">
<wg class="pp" role="pp" rule="PrepNp">
<w xml:id="o010010010011" ref="GEN 1:1!1" morph="R"
   pos="preposition" lemma="בְּ" unicode="בְּ">בְּ</w>
<w xml:id="o010010010012" ref="GEN 1:1!1" morph="Ncfsa"
   pos="noun" lemma="רֵאשִׁית">רֵאשִׁ֖ית</w></wg>
<w xml:id="o010010010021" ref="GEN 1:1!2"
   pos="verb" role="v" lemma="בָּרָא">בָּרָא</w>
<w xml:id="o010010010031" ref="GEN 1:1!3"
   pos="noun" role="s" lemma="אֱלֹהִים">אֱלֹהִים</w>
</wg></sentence></chapter>"""
NT_XML = """<book id="2JN" lang="el">
<sentence><wg class="cl" rule="S-O">
<wg class="np" role="s" rule="DetNP">
<w xml:id="n63001001001" ref="2JN 1:1!1"
   lemma="ὁ" morph="T-NSM">Ὁ</w>
<w xml:id="n63001001002" ref="2JN 1:1!2"
   lemma="πρεσβύτερος">πρεσβύτερος</w></wg>
<w xml:id="n63001001003" ref="2JN 1:1!3"
   lemma="ἐκλεκτός">ἐκλεκτῇ</w>
</wg></sentence></book>"""


def source_index():
    rows = []
    by_source = {}
    for canon, sources in (("ot", OT_IDS), ("nt", NT_IDS)):
        for source in sources:
            if source in ("o010010010012", "o010010010021",
                          "n63001001002", "n63001001003"):
                verse = source[1:9]
                target = {"o010010010012":1, "o010010010021":3,
                          "n63001001002":2, "n63001001003":3}[source]
                rows.append({
                    "canon": canon,
                    "original_macula_ids": [source],
                    "word_ids": [f"{verse}:{target}"],
                    "status": ("clear_bible_direct_word_only" if canon == "nt"
                               else "aquifer_original_surface_attested")})
                by_source[source] = [len(rows)-1]
            else:
                by_source[source] = []
    by_source["o010010010041"] = []  # extra index original absent source XML
    return {
        "by_original_macula_id": by_source,
        "unlinked_cause_by_original_macula_id": {
            OT_IDS[0]:tool.sampler.STRATA[1],
            OT_IDS[3]:tool.sampler.STRATA[0],
            NT_IDS[0]:tool.sampler.STRATA[2],
            "o010010010041":tool.sampler.STRATA[3],
        },
        "rows": rows,
    }


class SyntaxLowfatTests(unittest.TestCase):
    def ot(self):
        return tool.parse_original_syntax(OT_XML.encode(), "ot", OT_PATH)

    def nt(self):
        return tool.parse_original_syntax(NT_XML.encode(), "nt", NT_PATH)

    def test_original_morphemes_share_orthographic_word_ref_not_XML_ID(self):
        parsed = self.ot()
        self.assertEqual(len(parsed["tokens"]), 4)
        self.assertEqual(parsed["orthographic_words"]["GEN 1:1!1"],
                         [OT_IDS[0], OT_IDS[1]])
        self.assertEqual(parsed["tokens"][OT_IDS[0]]["original_lemma"], "בְּ")
        self.assertEqual(parsed["tokens"][OT_IDS[1]]["original_morphology"], "Ncfsa")
        self.assertEqual(parsed["tokens"][OT_IDS[0]]["original_surface"], "בְּ")
        self.assertEqual(parsed["tokens"][OT_IDS[1]]["original_surface"], "רֵאשִׁ֖ית")
        self.assertEqual(parsed["tokens"][OT_IDS[0]]["original_part_of_speech"],
                         "preposition")
        self.assertEqual(parsed["source_xml_sha256"],
                         hashlib.sha256(OT_XML.encode()).hexdigest())

    def test_prefer_actual_smallest_nested_source_constituent(self):
        parsed = self.ot()
        first = parsed["preferred_by_source"][OT_IDS[0]]
        self.assertEqual(first["original_group_class"], "pp")
        self.assertEqual(first["original_group_rule"], "PrepNp")
        self.assertEqual(first["original_macula_ids"], list(OT_IDS[:2]))
        fourth = parsed["preferred_by_source"][OT_IDS[-1]]
        self.assertEqual(fourth["original_group_class"], "cl")
        self.assertEqual(fourth["original_macula_ids"], list(OT_IDS))
        self.assertTrue(first["source_side_only_not_translated_phrase"])
        self.assertEqual(parsed["diagnostics"]["eligible_2_to_24_source_group"], 2)

    def test_nt_source_word_order_and_true_syntax_roles_preserved(self):
        parsed = self.nt()
        self.assertEqual(parsed["book"], "2JN")
        self.assertEqual(parsed["tokens"][NT_IDS[0]]["original_language"], "el")
        self.assertEqual(parsed["preferred_by_source"][NT_IDS[0]][
            "original_group_role"], "s")
        self.assertEqual(parsed["preferred_by_source"][NT_IDS[2]][
            "original_macula_ids"], list(NT_IDS))

    def test_anchor_cues_are_only_existing_authored_french_positions(self):
        index = source_index()
        ot = self.ot()
        french = {"01001001": "Au commencement Dieu créa"}
        cue = tool.review_cue(index, french, ot["preferred_by_source"][OT_IDS[0]])
        self.assertEqual(cue["french_anchor_word_ids"], ["01001001:1"])
        self.assertEqual(cue["french_cue_word_ids"], [])
        other = tool.review_cue(
            index, french, ot["preferred_by_source"][OT_IDS[3]])
        self.assertEqual(other["source_anchor_count"], 2)
        self.assertEqual(other["french_cue_word_ids"], [
            "01001001:1", "01001001:2", "01001001:3"])
        self.assertTrue(other["french_cue_is_not_original_phrase_translation"])
        self.assertFalse(other["multiple_original_ids_share_french_anchor"])
        self.assertEqual(index, source_index())

    def test_reordered_translation_anchors_are_recorded_not_assumed_equivalent(self):
        index = source_index()
        altered = copy.deepcopy(index)
        row_index = altered["by_original_macula_id"][OT_IDS[2]][0]
        altered["rows"][row_index]["word_ids"] = ["01001001:2"]
        row_index = altered["by_original_macula_id"][OT_IDS[1]][0]
        altered["rows"][row_index]["word_ids"] = ["01001001:4"]
        group = self.ot()["preferred_by_source"][OT_IDS[3]]
        cue = tool.review_cue(altered, {
            "01001001":"Au commencement Dieu créa"}, group)
        self.assertTrue(cue["unreviewed_reordering_witness"])
        self.assertEqual(cue["french_anchor_word_ids"], [
            "01001001:4", "01001001:2"])
        self.assertEqual(cue["french_cue_word_ids"], [
            "01001001:2", "01001001:3", "01001001:4"])
        # A French cue is not a guaranteed translation of original group.
        self.assertTrue(cue["french_cue_is_not_original_phrase_translation"])

    def test_missing_authored_verse_never_creates_french_words(self):
        cue = tool.review_cue(
            source_index(), {},
            self.ot()["preferred_by_source"][OT_IDS[3]])
        self.assertFalse(cue["exact_authored_french_verse_exists"])
        self.assertEqual(cue["french_anchor_word_ids"], [])
        self.assertEqual(cue["french_cue_word_ids"], [])

    def test_syntax_rejects_book_verse_or_duplicate_token_id(self):
        wrong = OT_XML.replace('GEN 1:1!2', 'GEN 1:2!2')
        with self.assertRaisesRegex(ValueError, "reference disagreement"):
            tool.parse_original_syntax(wrong.encode(), "ot", OT_PATH)
        wrong = OT_XML.replace('GEN 1:1!2', 'EXO 1:1!2')
        with self.assertRaisesRegex(ValueError, "reference disagreement"):
            tool.parse_original_syntax(wrong.encode(), "ot", OT_PATH)
        dup = OT_XML.replace("o010010010031", "o010010010021")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            tool.parse_original_syntax(dup.encode(), "ot", OT_PATH)
        with self.assertRaisesRegex(ValueError, "wrong Testament"):
            tool.parse_original_syntax(OT_XML.encode(), "nt", OT_PATH)

    def test_cross_verse_syntax_group_is_not_silently_split(self):
        bad = NT_XML.replace('n63001001003" ref="2JN 1:1!3"',
                             'n63001002001" ref="2JN 1:2!1"')
        parsed = tool.parse_original_syntax(bad.encode(), "nt", NT_PATH)
        self.assertEqual(parsed["diagnostics"]["cross_verse_group_rejected"], 1)
        self.assertEqual(
            parsed["preferred_by_source"][NT_IDS[0]]["original_macula_ids"],
            list(NT_IDS[:2]))
        self.assertNotIn("n63001002001", parsed["preferred_by_source"])

    def test_full_private_review_pilot_preserves_index_and_never_approves(self):
        original = source_index()
        untouched = copy.deepcopy(original)
        authored = {
            "01001001": "Au commencement Dieu créa",
            "63001001": "L'ancien aime les élus",
        }
        parsed = [self.ot(), self.nt()]
        private, report = tool.synthesize(
            original, authored, parsed,
            expected_pilot_files=(("ot", OT_PATH), ("nt", NT_PATH)))
        self.assertEqual(original, untouched)
        self.assertEqual(report["source_xml_total_original_token_ids"], 7)
        self.assertEqual(report["original_source_XML_ids_already_in_correspondence_index"], 7)
        self.assertEqual(report["correspondence_index_source_ids_not_in_selected_XML"], 1)
        self.assertEqual(report["unresolved_original_ids_in_selected_source_documents"], 3)
        self.assertEqual(report["source_verse_count"], 2)
        self.assertEqual(report["source_verses_with_exact_authored_LSG"], 2)
        self.assertEqual(report["unresolved_original_by_testament"]["ot"][
            "within_multi_morpheme_orthographic_word"], 1)
        self.assertEqual(report["unresolved_original_by_testament"]["ot"][
            "same_original_word_has_preexisting_french_anchor"], 1)
        self.assertEqual(report["unresolved_original_by_testament"]["nt"][
            "in_small_macula_syntax_constituent"], 1)
        self.assertEqual(report["new_individually_approved_MACULA_original_ids"], 0)
        self.assertEqual(report["new_semantically_approved_source_phrases"], 0)
        self.assertFalse(report["publication_authorized"])
        self.assertTrue(report["source_text_in_public_receipt"] is False)
        self.assertTrue(all(not item["original_phrase_semantically_verified"]
                            and item["automatic_word_links_added"] == 0
                            for item in private["cases"]))
        self.assertEqual(
            len({c["original_macula_id"] for c in private["cases"]}), 3)
        self.assertEqual(private["source_tokens_not_in_existing_index"], [])
        self.assertEqual(private["indexed_source_tokens_missing_from_selected_lowfat"],
                         ["o010010010041"])

    def test_private_data_reproducible_without_leaking_to_public_report(self):
        parsed = [self.ot(), self.nt()]
        private, report = tool.synthesize(source_index(), {
            "01001001": "Au commencement Dieu créa",
            "63001001": "L'ancien aime les élus"}, parsed,
            expected_pilot_files=(("ot", OT_PATH), ("nt", NT_PATH)))
        packed = tool.phrase.compressed_private(private)
        self.assertEqual(packed, tool.phrase.compressed_private(private))
        self.assertIn("בְּ", json.dumps(private, ensure_ascii=False))
        self.assertNotIn("בְּ", json.dumps(report, ensure_ascii=False))
        self.assertNotIn("commencement", json.dumps(report))
        self.assertNotIn("original_macula_id", json.dumps(report))
        self.assertEqual(json.loads(__import__("gzip").decompress(packed)),
                         private)


if __name__ == "__main__":
    unittest.main()
