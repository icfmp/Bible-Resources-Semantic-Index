"""Small negative and positive tests for the source-bound alignment validator."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parent / "validate_chapter.py"
spec = importlib.util.spec_from_file_location("validate_chapter", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ValidateChapterTest(unittest.TestCase):
    def setUp(self):
        self.h = b'<chapter><w xml:id="a" ref="GEN 1:1!1" pos="noun">x</w></chapter>'
        self.f = b'<osis><verse sID="Gen.1.1"/>Mot<note>ignore</note>.<verse eID="Gen.1.1"/></osis>'
        self.d = {"scope": "Gen.1.1–1",
                  "sources": {"macula": {"blob": module.git_blob(self.h)},
                              "lsg": {"expected_current_blob": module.git_blob(self.f),
                                      "chapter_prose_sha256": hashlib.sha256(b"Mot.").hexdigest()}},
                  "relations": [{"kind": "translation", "hebrew": ["a"], "french": [[1, 1, 0, 3]]}],
                  "statistics": {"relations": 1, "hebrew_units": 1, "french_units": 1,
                                 "lexical_content_units": 1, "lexical_content_translation": 1,
                                 "translation": {"relations": 1, "hebrew_units": 1, "french_units": 1, "single_original_relations": 1},
                                 "contextual": {"relations": 0, "hebrew_units": 0, "french_units": 0, "single_original_relations": 0}}}
    def test_valid(self):
        self.assertEqual(module.validate(self.d, self.h, self.f), self.d["statistics"])
    def test_bad_offset(self):
        self.d["relations"][0]["french"][0][3] = 2
        with self.assertRaisesRegex(ValueError, "offset"):
            module.validate(self.d, self.h, self.f)
    def test_wrong_source(self):
        with self.assertRaisesRegex(ValueError, "blob mismatch"):
            module.validate(self.d, self.h, self.f + b" ")
    def test_wrong_id(self):
        self.d["relations"][0]["hebrew"] = ["b"]
        with self.assertRaisesRegex(ValueError, "Unknown MACULA ID"):
            module.validate(self.d, self.h, self.f)
    def test_missing_coverage(self):
        self.d["relations"].clear()
        with self.assertRaisesRegex(ValueError, "coverage"):
            module.validate(self.d, self.h, self.f)
    def test_duplicate(self):
        self.d["relations"].append(copy.deepcopy(self.d["relations"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate relation"):
            module.validate(self.d, self.h, self.f)

if __name__ == "__main__":
    unittest.main()
