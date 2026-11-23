"""Real-record proof that large-batch source corrections are source-pinned and reversible."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DIRECT = {
    "groups/Israel": [
        "wlc",
        [
            [
                "o020010090061",
                "o020010090071"
            ],
            [
                "o020190030161",
                "o020190030171"
            ]
        ]
    ],
    "groups/Midian": [
        "wlc",
        [
            [
                "o010360350101"
            ]
        ]
    ],
    "groups/Gershon": [
        "wlc",
        [
            [
                "o040040410041",
                "o040040410051"
            ]
        ]
    ],
    "groups/Kohath": [
        "wlc",
        [
            [
                "o040070090013",
                "o040070090021"
            ]
        ]
    ],
    "groups/Gibeon": [
        "wlc",
        [
            [
                "o060090030012",
                "o060090030021"
            ]
        ]
    ],
    "fauna/CreepingAnimal": [
        "wlc",
        [
            [
                "o030050020181"
            ],
            [
                "o050320240131"
            ]
        ]
    ],
    "people/Jerubbaal": [
        "SBLGNT",
        [
            [
                "n58011032012"
            ]
        ]
    ],
    "realia/Container": [
        "SBLGNT",
        [
            [
                "n41014003017"
            ],
            [
                "n41014003024"
            ]
        ]
    ],
    "places/Bethlehem.2": [
        "wlc",
        [
            [
                "o070120080062",
                "o070120080071"
            ],
            [
                "o070120100042",
                "o070120100051"
            ]
        ]
    ],
    "people/Basemath.3": [
        "wlc",
        [
            [
                "o010280090071"
            ]
        ]
    ],
    "people/Lord": [
        "SBLGNT",
        [
            [
                "n50002005009"
            ],
            [
                "n50002010005"
            ]
        ]
    ],
    "places/Ephron.1": [
        "wlc",
        [
            [
                "o060150090121",
                "o060150090131"
            ]
        ]
    ]
}
KEY_CORRECTIONS = {
    "deities/Chemosh": ("04021009", "04021029"),
    "groups/Ammon": ("05023003", "05023004"),
    "flora/Weed": ("18031004", "18031040")
}

def read(source):
    kind,name = source.split("/",1)
    return json.loads((ROOT/"data"/"entities"/kind/(name+".json")).read_text(encoding="utf-8"))

class ThirdLargeBatchTests(unittest.TestCase):
    def test_direct_witnesses_are_exact_and_originals_are_recoverable(self):
        self.assertEqual(len(DIRECT),12)
        for source,(corpus,groups) in DIRECT.items():
            with self.subTest(source=source):
                rec=read(source)
                changes=rec["bsi"]["editorial_field_changes"]
                self.assertTrue(changes)
                receipt=changes[-1]
                self.assertTrue(receipt["reason"])
                self.assertTrue(receipt["evidence"])
                before=receipt["replaced_field_values"]["before"]
                after=receipt["replaced_field_values"]["after"]
                self.assertEqual(after["references"],rec["references"])
                self.assertEqual(after["explicit_instances"],rec["explicit_instances"])
                self.assertEqual(len(rec["bsi"]["source_sha256"]),64)
                self.assertEqual(rec["bsi"]["review_status"],"editorially_reviewed")
                self.assertTrue(set(before["references"]).issubset(rec["references"]))
                for group in groups:
                    self.assertIn(group,rec["explicit_instances"][corpus])
                    self.assertNotIn(group,before["explicit_instances"].get(corpus,[]))
                    self.assertEqual(len({w[1:9] for w in group}),1)
                    verse=group[0][1:9]
                    self.assertIn(verse,rec["references"])
                    if source != "places/Ephron.1":
                        self.assertIn(verse,rec["key_references"])
                self.assertEqual(len(rec["explicit_instances"][corpus]),
                                 len(before["explicit_instances"].get(corpus,[]))+len(groups))

    def test_three_misattributed_key_verses_corrected_not_erased(self):
        self.assertEqual(len(KEY_CORRECTIONS),3)
        for source,(wrong,right) in KEY_CORRECTIONS.items():
            with self.subTest(source=source):
                rec=read(source)
                self.assertNotIn(wrong,rec["key_references"])
                self.assertIn(right,rec["key_references"])
                self.assertIn(right,rec["references"])
                receipt=rec["bsi"]["editorial_field_changes"][-1]
                self.assertEqual(receipt["action"],
                                 "correct_wrong_inherited_key_verse_to_direct_source_attested_verse")
                self.assertIn(wrong,receipt["replaced_field_values"]["before"]["key_references"])
                self.assertIn(right,receipt["replaced_field_values"]["after"]["key_references"])
                self.assertTrue(receipt["reason"] and receipt["evidence"])
                self.assertTrue(rec["explicit_instances"])

    def test_mountain_ephron_contextual_key_does_not_fake_name_in_joshua_18(self):
        ephron=read("places/Ephron.1")
        self.assertEqual(ephron["references"],["06015009"])
        self.assertEqual(ephron["key_references"],["06018015"])
        self.assertEqual(ephron["localizations"]["eng"]["preferred_label"],
                         "Mount Ephron (Joshua 15:9)")
        self.assertEqual(ephron["explicit_instances"]["wlc"],
                         [["o060150090121","o060150090131"]])
        self.assertEqual(ephron["bsi"]["editorial_field_changes"][-1]["action"],
                         "restore_true_mount_ephron_verse_instead_of_contextual_border")

    def test_homonymous_people_and_species_not_auto_conflated(self):
        gibeon=read("groups/Gibeon")
        bethlehem=read("places/Bethlehem.2")
        israel=read("groups/Israel")
        self.assertIn("06009003",gibeon["references"])
        self.assertIn("07012008",bethlehem["references"])
        self.assertIn("07012010",bethlehem["references"])
        self.assertEqual(israel["bsi"]["canonical_id"],"group:Israel")
        self.assertNotIn("01046011",read("groups/Kohath")["references"])
        self.assertNotIn("01046011",read("groups/Gershon")["references"])
        self.assertIn("44010012",read("fauna/CreepingAnimal")["references"])

if __name__=="__main__":
    unittest.main()
