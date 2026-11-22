"""Native BSI editing must permit new evidenced records and protect all imported IDs."""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_bsi_builder", ROOT / "scripts" / "build_native_index.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class NativeGrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"
        shutil.copytree(ROOT / "data", self.data)

    def add_native_work(self):
        work = self.data / "entities" / "works"
        work.mkdir(exist_ok=True)
        path = work / "Fixture.json"
        path.write_text(json.dumps({
            "id": "work:Fixture", "primary_id": "work:Fixture",
            "type": "literary_work", "references": ["01001001"],
            "key_references": ["01001001"],
            "bsi": {
                "origin": "bsi", "source_id": "bsi:work:Fixture",
                "source_primary_id": "bsi:work:Fixture",
                "canonical_id": "work:Fixture",
                "review_status": "editorially_reviewed",
                "editorial_reason": "Synthetic test case, not a real biblical entity",
                "editorial_evidence": ["Test fixture only: Genesis 1:1"],
            },
        }, ensure_ascii=False), encoding="utf-8")
        return path

    def test_current_builder_does_not_import_historical_compiler(self):
        self.assertEqual(Path(builder.core.__file__).name, "entity_index_core.py")
        self.assertNotIn("compile_index.py",
                         (ROOT / "scripts" / "build_native_index.py").read_text())

    def test_new_reviewed_entity_does_not_rewrite_historical_baseline(self):
        baseline = builder.build(self.data)
        path = self.add_native_work()
        current = builder.build(self.data)
        self.assertEqual(len(current["entities"]), len(baseline["entities"]) + 1)
        self.assertEqual(len(current["quarantined"]), len(baseline["quarantined"]))
        self.assertEqual(current["statistics"]["source_records"], baseline["statistics"]["source_records"])
        self.assertEqual(current["by_word"], baseline["by_word"])
        self.assertEqual(current["unattested_source_words"], baseline["unattested_source_words"])
        self.assertEqual(current["unattested_source_verses"], baseline["unattested_source_verses"])
        self.assertEqual(current["qualified_source_references"], baseline["qualified_source_references"])
        old = {e["source_id"]: e for e in baseline["entities"]}
        new = {e["source_id"]: e for e in current["entities"]}
        self.assertEqual({sid: new[sid] for sid in old}, old)
        self.assertEqual(new["bsi:work:Fixture"]["id"], "work:Fixture")
        self.assertIsNone(new["bsi:work:Fixture"]["source_sha256"])
        self.assertTrue(path.exists())

    def test_nonworking_translated_names_are_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["localizations"]["fra"] = {"preferred_label": "Marie"}
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Redundant translated label"):
            builder.build(self.data)

    def test_source_biographies_are_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["localizations"]["eng"]["descriptions"] = [
            {"description": "Old inherited paragraph"}
        ]
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Encyclopedia descriptions forbidden"):
            builder.build(self.data)

    def test_top_level_encyclopedia_prose_is_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["descriptions"] = ["Old imported biography"]
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Encyclopedia descriptions forbidden"):
            builder.build(self.data)

    def test_obsolete_prose_review_hold_is_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["bsi"]["inherited_localizations"] = {
            "status": "withheld_pending_review", "source": "acai",
            "reason": "Synthetic obsolete hold", "fields": ["descriptions"],
        }
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Obsolete inherited encyclopedia prose hold"):
            builder.build(self.data)

    def test_nonworking_language_review_hold_is_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["bsi"]["inherited_localizations"] = {
            "status": "withheld_pending_review", "source": "acai",
            "reason": "Synthetic nonworking-language hold",
            "fields": ["fra.preferred_label"],
        }
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Redundant translated localization hold"):
            builder.build(self.data)

    def test_imported_identity_must_keep_english_working_label(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["localizations"]["eng"]["preferred_label"] = ""
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Imported entity lacks English working identity label"):
            builder.build(self.data)

    def test_duplicate_json_keys_cannot_override_original_fields(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        original = path.read_text(encoding="utf-8")
        path.write_text('{"duplicate":1,"duplicate":2,' + original.lstrip()[1:],
                        encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON object key"):
            builder.build(self.data)

    def test_nonstandard_json_numbers_are_rejected(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        original = path.read_text(encoding="utf-8")
        path.write_text('{"nonstandard":NaN,' + original.lstrip()[1:],
                        encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Nonstandard JSON number"):
            builder.build(self.data)

    def test_unknown_entity_category_is_not_silently_ignored(self):
        unexpected = self.data / "entities" / "unknown_category"
        unexpected.mkdir()
        (unexpected / "Unindexed.json").write_text('{"id":"fake:Foo"}',
                                                    encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unsupported native entity category"):
            builder.build(self.data)

    def test_nested_entity_json_is_not_silently_ignored(self):
        nested = self.data / "entities" / "people" / "nested"
        nested.mkdir()
        (nested / "Unindexed.json").write_text('{"id":"person:Unindexed"}',
                                               encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unindexed or nested native entity JSON"):
            builder.build(self.data)

    def test_uppercase_json_entity_cannot_be_silently_skipped(self):
        rogue = self.data / "entities" / "people" / "Unindexed.JSON"
        rogue.write_text('{"id": "person:Unindexed"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unindexed or nested native entity JSON"):
            builder.build(self.data)

    def test_uppercase_json_quarantine_cannot_be_silently_skipped(self):
        rogue = self.data / "quarantined" / "people" / "Unindexed.Json"
        rogue.write_text('{"id": "person:Unindexed"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unindexed or nested native entity JSON"):
            builder.build(self.data)

    def test_native_data_symlinks_are_rejected(self):
        source = self.data / "entities" / "people" / "Mary.2.json"
        alias = self.data / "entities" / "people" / "DuplicateMary.json"
        alias.symlink_to(source.name)
        with self.assertRaisesRegex(ValueError, "Native entity symlinks are not permitted"):
            builder.build(self.data)

    def test_restricted_keyterms_are_rejected_in_quarantine(self):
        restricted = self.data / "quarantined" / "keyterms"
        restricted.mkdir()
        payload = {
            "bsi": {
                "source_id": "keyterm:Unpublished", "origin": "acai",
                "source_sha256": "a" * 64, "state": "quarantined",
                "reason": "Synthetic fixture, not cleared for redistribution",
                "evidence": ["Synthetic fixture only"],
            },
        }
        (restricted / "Unpublished.json").write_text(
            json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Restricted keyterm record"):
            builder.build(self.data)

    def test_imported_source_fingerprint_rejects_nonhex_bytes(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["bsi"]["source_sha256"] = "g" * 64
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid imported source SHA-256"):
            builder.build(self.data)

    def test_quarantined_source_provenance_is_validated(self):
        path = self.data / "quarantined" / "people" / "Shiloh.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        for field, new_value, message in (
            ("source_sha256", "z" * 64, "Invalid imported source SHA-256"),
            ("reason", "", "Quarantine needs a documented reason"),
            ("evidence", [], "Quarantine needs source evidence"),
        ):
            with self.subTest(field=field):
                record = copy.deepcopy(original)
                record["bsi"][field] = new_value
                path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    builder.build(self.data)
        path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        builder.build(self.data)

    def test_native_entities_cannot_claim_acai_source_hash(self):
        path = self.add_native_work()
        record = json.loads(path.read_text(encoding="utf-8"))
        record["bsi"]["source_sha256"] = "a" * 64
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must not claim an ACAI source SHA-256"):
            builder.build(self.data)

    def test_original_word_ids_reject_unicode_digit_lookalikes(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        original = record["explicit_instances"]["SBLGNT"][0][0]
        self.assertTrue(original[1:].isascii())
        # An Arabic-Indic digit passes Python str.isdigit(), but does not
        # belong to the exact pinned MACULA SBLGNT source word ID.
        record["explicit_instances"]["SBLGNT"][0][0] = (
            original[0] + "\u0661" + original[2:])
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformed original word ID"):
            builder.build(self.data)

    def test_original_word_ids_reject_nonstring_token(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["explicit_instances"]["SBLGNT"][0][0] = 12345
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "word prefix incompatible"):
            builder.build(self.data)

    def test_historical_source_cannot_disappear(self):
        (self.data / "entities" / "people" / "Jashar.json").unlink()
        with self.assertRaisesRegex(ValueError, "Imported ACAI entity identities changed"):
            builder.build(self.data)

    def test_unreviewed_new_native_entry_is_rejected(self):
        path = self.add_native_work()
        payload = json.loads(path.read_text())
        del payload["bsi"]["editorial_evidence"]
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lacks source evidence"):
            builder.build(self.data)

    def test_new_work_must_have_stable_typed_identity(self):
        for field, replacement, message in (
            ("type", "person", "Invalid typed canonical entity identity"),
            ("id", "person:Fixture", "Invalid typed canonical entity identity"),
            ("id", "work:Other", "Incorrect BSI-native identity type or owner"),
            ("primary_id", "work:Other", "Incorrect BSI-native identity type or owner"),
        ):
            with self.subTest(field=field):
                path = self.add_native_work()
                record = json.loads(path.read_text(encoding="utf-8"))
                record[field] = replacement
                path.write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    builder.build(self.data)
                path.unlink()

    def test_new_work_canonical_target_must_exist(self):
        path = self.add_native_work()
        record = json.loads(path.read_text(encoding="utf-8"))
        record["bsi"]["canonical_id"] = "work:Unknown"
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Incorrect BSI-native identity type or owner"):
            builder.build(self.data)

    def test_imported_alias_cannot_target_missing_current_identity(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["bsi"]["canonical_id"] = "person:Uninvented"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "Canonical target missing from current index"):
            builder.build(self.data)

    def test_imported_entity_kind_must_match_typed_current_identity(self):
        path = self.data / "entities" / "people" / "Mary.2.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["type"] = "place"
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid typed canonical entity identity"):
            builder.build(self.data)

    def test_source_id_mismatch_is_rejected(self):
        path = self.add_native_work()
        payload = json.loads(path.read_text())
        payload["bsi"]["source_id"] = "bsi:person:WrongCategory"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Incorrect BSI-native identity"):
            builder.build(self.data)


if __name__ == "__main__":
    unittest.main()
