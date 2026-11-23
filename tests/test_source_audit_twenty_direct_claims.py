"""Actual data evidence for twenty independently reviewed pinned original-word fixes.

These checks enforce complete token groups, historic source provenance and
reversible before/after receipts. No entire source verse is auto-promoted.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLAIMS = {
    "places/Goiim.1": [
        "wlc",
        [
            [
                "o010140010141"
            ],
            [
                "o010140090071"
            ]
        ]
    ],
    "places/Goiim.2": [
        "wlc",
        [
            [
                "o060120230071"
            ]
        ]
    ],
    "places/Havilah": [
        "wlc",
        [
            [
                "o010250180022"
            ],
            [
                "o090150070052"
            ]
        ]
    ],
    "places/Nebo.3": [
        "wlc",
        [
            [
                "o150100430021"
            ]
        ]
    ],
    "places/Sheba.2": [
        "wlc",
        [
            [
                "o110100010021"
            ]
        ]
    ],
    "places/Shihor": [
        "wlc",
        [
            [
                "o130130050071"
            ]
        ]
    ],
    "places/Gilgal.3": [
        "wlc",
        [
            [
                "o060040190092"
            ],
            [
                "o060040200122"
            ]
        ]
    ],
    "places/Samaria.2": [
        "wlc",
        [
            [
                "o120170240111"
            ],
            [
                "o120170240171"
            ]
        ]
    ],
    "people/Jehoash.2": [
        "wlc",
        [
            [
                "o120130090081"
            ],
            [
                "o120130120031"
            ],
            [
                "o120130130021"
            ],
            [
                "o120130130101"
            ]
        ]
    ],
    "people/Jerubbaal": [
        "wlc",
        [
            [
                "o070060110132"
            ]
        ]
    ],
    "people/Jeshua.9": [
        "wlc",
        [
            [
                "o150100180091"
            ],
            [
                "o370010010231"
            ]
        ]
    ],
    "people/Caesar.2": [
        "SBLGNT",
        [
            [
                "n44018002022"
            ]
        ]
    ],
    "people/Caesar.4": [
        "SBLGNT",
        [
            [
                "n42003001007",
                "n42003001008"
            ]
        ]
    ],
    "people/Cephas": [
        "SBLGNT",
        [
            [
                "n40004018014"
            ]
        ]
    ],
    "people/Joses.3": [
        "SBLGNT",
        [
            [
                "n40027056013"
            ]
        ]
    ],
    "people/Edom": [
        "wlc",
        [
            [
                "o010250250091"
            ],
            [
                "o010250260081"
            ],
            [
                "o010250270041"
            ],
            [
                "o010250280041"
            ],
            [
                "o010250290051"
            ]
        ]
    ],
    "people/Pharaoh": [
        "wlc",
        [
            [
                "o240440300071",
                "o240440300081"
            ]
        ]
    ],
    "realia/Net": [
        "SBLGNT",
        [
            [
                "n54003007016"
            ]
        ]
    ],
    "realia/Plaster": [
        "wlc",
        [
            [
                "o030140420112"
            ]
        ]
    ],
    "realia/Seal": [
        "wlc",
        [
            [
                "o170080080092"
            ]
        ]
    ]
}


class ActualSourceDirectWitnessTests(unittest.TestCase):
    def test_twenty_independent_cases_complete_and_reversible(self):
        self.assertEqual(len(CLAIMS), 20)
        for identity, (corpus, groups) in CLAIMS.items():
            with self.subTest(identity=identity):
                category, name = identity.split("/", 1)
                path = ROOT / "data" / "entities" / category / (name + ".json")
                record = json.loads(path.read_text(encoding="utf-8"))
                before = record["bsi"]["editorial_field_changes"][-1]
                self.assertTrue(before["reason"])
                self.assertTrue(before["evidence"])
                self.assertEqual(before["replaced_field_values"]["after"]["references"],
                                 record["references"])
                self.assertEqual(before["replaced_field_values"]["after"]["explicit_instances"],
                                 record["explicit_instances"])
                original = before["replaced_field_values"]["before"]
                self.assertEqual(record["bsi"]["review_status"], "editorially_reviewed")
                self.assertEqual(len(record["bsi"]["source_sha256"]), 64)
                source_id = record["bsi"]["source_id"]
                self.assertEqual(source_id, category.replace("people", "person").replace("places", "place") + ":" + name)
                self.assertTrue(record["bsi"]["editorial_evidence"])
                self.assertTrue(set(original["references"]).issubset(set(record["references"])))
                for group in groups:
                    self.assertIn(group, record["explicit_instances"][corpus])
                    self.assertNotIn(group, original["explicit_instances"].get(corpus, []))
                    self.assertTrue(all(word[1:9] == group[0][1:9] for word in group))
                    self.assertIn(group[0][1:9], record["references"])
                    self.assertIn(group[0][1:9], record["key_references"])
                self.assertEqual(
                    len(record["explicit_instances"][corpus]),
                    len(original["explicit_instances"].get(corpus, [])) + len(groups))

    def test_no_neighboring_false_positive_promoted(self):
        plaster = json.loads((ROOT / "data/entities/realia/Plaster.json").read_text())
        seal = json.loads((ROOT / "data/entities/realia/Seal.json").read_text())
        shihor = json.loads((ROOT / "data/entities/places/Shihor.json").read_text())
        net = json.loads((ROOT / "data/entities/realia/Net.json").read_text())
        self.assertNotIn(["o030140420082"], plaster["explicit_instances"]["wlc"])
        self.assertNotIn(["o170080080102"], seal["explicit_instances"]["wlc"])
        self.assertNotIn(["o170080080192"], seal["explicit_instances"]["wlc"])
        self.assertNotIn(["o130130050081"], shihor["explicit_instances"]["wlc"])
        self.assertNotIn(["n54003007016"], net["explicit_instances"].get("wlc", []))


if __name__ == "__main__":
    unittest.main()
