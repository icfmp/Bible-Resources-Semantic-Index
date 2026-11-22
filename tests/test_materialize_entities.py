"""Native BSI materialization protects every old decision and original source byte."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "materialize_entities.py"
spec = importlib.util.spec_from_file_location("bsi_native_migration", SCRIPT)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / "source"
        self.out = root / "output"
        for category in migration.CATEGORIES:
            (self.source / category / "json").mkdir(parents=True)
        self.lock = {
            "schema_version": 1,
            "source_repository": "https://example.org/source",
            "source_commit": "a" * 40,
            "source_license": "CC BY-SA 4.0",
            "source_credit": "source test",
            "reviewed_hebrew_source": "wlc-test",
            "reviewed_greek_source": "nt-test",
            "source_editions": {
                "wlc": {"edition": "wlc-test", "word_id_prefix": "o", "word_id_digits": 12},
                "sblgnt": {"edition": "nt-test", "word_id_prefix": "n", "word_id_digits": 11},
            },
            "source_corpora": {"wlc": "wlc", "sblgnt": "sblgnt", "SBLGNT": "sblgnt"},
            "source_records_expected": 3,
        }
        self.original = {
            "id": "person:Jashar", "primary_id": "person:Jashar",
            "type": "person",
            "references": ["06010013"],
            "key_references": ["06010013"],
            "explicit_instances": {"wlc": [["o060100130142"]]},
            "pronominal_referents": {},
            "subject_referents": {},
            "localizations": {"fra": {"preferred_label": "livre original"}},
            "relationships": ["person:Other"],
        }
        self.keyterm = {
            "id": "keyterm:Ability", "primary_id": "keyterm:Ability",
            "references": [], "key_references": [], "localizations": {"fra": {"preferred_label": "Capacité"}},
        }
        self.quarantine = {
            "id": "person:Duplicate", "primary_id": "person:Duplicate",
            "references": [], "key_references": [],
        }
        self.write("people", "Jashar", self.original)
        self.write("people", "Duplicate", self.quarantine)
        self.write("keyterms", "Ability", self.keyterm)
        self.editorial = {
            "schema_version": 1,
            "decisions": [
                {"source_id": "person:Jashar", "action": "replace_identity",
                 "id": "work:BookOfJashar", "kind": "literary_work",
                 "canonical_id": "work:BookOfJashar",
                 "reason": "Historical work rather than a person",
                 "evidence": ["Joshua 10:13"]},
                {"source_id": "person:Duplicate", "action": "quarantine",
                 "reason": "Not an independent entity",
                 "evidence": ["Reviewed identity source"]},
            ],
        }

    def write(self, category, name, payload):
        (self.source / category / "json" / (name + ".json")).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def migrate(self, *, restricted=False):
        return migration.materialize(
            self.source, self.out, lock=self.lock, editorial=self.editorial,
            absences=None, verse_absences=None, qualifications=None,
            include_restricted=restricted)

    def test_changes_are_materialized_once_without_losing_original_fields(self):
        before = (self.source / "people/json/Jashar.json").read_bytes()
        result = self.migrate()
        active = json.loads((self.out / "entities/people/Jashar.json").read_text())
        self.assertEqual(active["id"], "work:BookOfJashar")
        self.assertEqual(active["primary_id"], "work:BookOfJashar")
        self.assertEqual(active["type"], "literary_work")
        self.assertEqual(active["bsi"]["source_id"], "person:Jashar")
        self.assertEqual(active["bsi"]["editorial_reason"], "Historical work rather than a person")
        self.assertEqual(active["localizations"], self.original["localizations"])
        self.assertEqual(active["relationships"], self.original["relationships"])
        self.assertEqual(active["explicit_instances"], self.original["explicit_instances"])
        self.assertEqual((self.source / "people/json/Jashar.json").read_bytes(), before)
        self.assertEqual(result["source_records"], 3)
        self.assertEqual(result["restricted_unpublished_keyterms"], 1)
        self.assertEqual(result["written_records"], 2)
        self.assertFalse((self.out / "entities/keyterms/Ability.json").exists())
        quarantined = json.loads((self.out / "quarantined/people/Duplicate.json").read_text())
        self.assertEqual(quarantined["id"], "person:Duplicate")
        self.assertEqual(quarantined["bsi"]["state"], "quarantined")
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            self.migrate()

    def test_restricted_records_only_in_explicit_local_review(self):
        result = self.migrate(restricted=True)
        self.assertEqual(result["written_records"], 3)
        self.assertEqual(result["restricted_unpublished_keyterms"], 0)
        self.assertTrue((self.out / "entities/keyterms/Ability.json").is_file())


if __name__ == "__main__":
    unittest.main()
