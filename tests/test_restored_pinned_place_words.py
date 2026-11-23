"""Exact pinned Macula original-word witnesses for corrected named places."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Every approved item is anchored to an actual pinned-original word and
# an independently reviewed matching geographical identity; historical
# ambiguities remain deliberately unpromoted.
REVIEWED = {
    "Bealoth.2": ("wlc", ["11004016"], [["o110040160052"]]),
    "Edrei.2": ("wlc", ["06019037"], [["o060190370022"]]),
    "Ether.2": ("wlc", ["06019007"], [["o060190070032"]]),
    "Gedor.4": ("wlc", ["13012008"], [["o130120080062"]]),
    "Gilgal.4": ("wlc", ["06015007"], [["o060150070092"]]),
    "Hammon.2": ("wlc", ["13006061"], [["o130060610091"]]),
    "Jericho.2": ("SBLGNT",
                  ["40020029", "41010046", "42010030", "42018035"],
                  [["n40020029005"], ["n41010046004"], ["n41010046009"],
                   ["n42010030012"], ["n42018035008"]]),
    "Kedesh.3": ("wlc", ["13006057"], [["o130060570041"]]),
    "Kir.2": ("wlc", ["23015001"], [["o230150010121"]]),
    "Moriah": ("wlc", ["01022002"], [["o010220020162"]]),
    "Nobah.2": ("wlc", ["07008011"], [["o070080110072"]]),
    "Pishon.1": ("wlc", ["01002011"], [["o010020110031"]]),
    "Ramah.6": ("wlc", ["06019029"], [["o060190290032"]]),
    "Ramah.7": ("wlc", ["16011033"], [["o160110330021"]]),
    "Remeth.1": ("wlc", ["06019021"], [["o060190210012"]]),
    "Ebenezer.2": ("wlc", ["09007012"],
                   [["o090070120131", "o090070120141"]]),
    "Gibeah.1": ("wlc", ["09010026", "09011004", "23010029"],
                 [["o090100260051"], ["o090110040031"],
                  ["o230100290081"]]),
    "Samaria.2": ("SBLGNT", ["42017011", "43004004"],
                  [["n42017011013"], ["n43004004007"]]),
    "Judea.2": ("wlc", ["15005008"], [["o150050080062"]]),
}


def native_place(name):
    return json.loads(
        (ROOT / "data" / "entities" / "places" / f"{name}.json")
        .read_text(encoding="utf-8"))


class ReviewedOriginalWordPlaceTests(unittest.TestCase):
    def test_original_word_ids_verses_and_editorial_receipts_unchanged(self):
        for name, (corpus, verses, groups) in REVIEWED.items():
            with self.subTest(name=name):
                o = native_place(name)
                self.assertEqual(o["id"], "place:" + name)
                self.assertEqual(o["references"], verses)
                self.assertEqual(o["explicit_instances"], {corpus: groups})
                self.assertTrue(all(v in o["key_references"] for v in verses))
                self.assertEqual(o["bsi"]["review_status"], "source_unreviewed")
                self.assertEqual(len(o["bsi"]["source_sha256"]), 64)
                receipts = [x for x in o["bsi"]["editorial_field_changes"]
                            if x["action"] == "restore_direct_original_word_and_verse_witness"]
                self.assertEqual(len(receipts), 1)
                self.assertEqual(receipts[0]["added_reference_values"],
                                 {"references": verses})
                self.assertEqual(receipts[0]["added_original_word_groups"],
                                 {corpus: groups})
                self.assertTrue(receipts[0]["reason"].strip())
                self.assertTrue(receipts[0]["evidence"])

    def test_lydia_in_acts_is_person_not_the_geographical_region(self):
        place = native_place("Lydia")
        person = json.loads(
            (ROOT / "data" / "entities" / "people" / "Lydia.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(place["key_references"], [])
        self.assertEqual(place["references"], [])
        self.assertFalse(place["mentioned_in_bible"])
        self.assertTrue(place["non_biblical"])
        self.assertEqual(person["explicit_instances"]["SBLGNT"],
                         [["n44016014005"], ["n44016040009"]])
        receipts = [x for x in place["bsi"]["editorial_field_changes"]
                    if x["action"] == "correct_person_name_conflated_with_geographic_region"]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["removed_relation_values"],
                         {"key_references": ["44016040"]})


if __name__ == "__main__":
    unittest.main()
