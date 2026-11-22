"""Published V1 consumer feasibility: strict, source-pinned and no app calls.

All ZIPs below are synthetic in-memory fixtures; none is a reissued release.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_v1_archive_inspection", ROOT / "scripts" / "inspect_v1_published_assets.py")
inspect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspect)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n").encode()


def public_index(kind):
    if kind == "entities":
        return {
            "format": "bible-entity-index",
            "schema_version": 1,
            "distribution_profile": {"name": "bsi-v0.1-without-keyterms",
                                     "excluded_kinds": ["keyterm"]},
            "entities": [{"id": "person:Mary.2", "kind": "person"}],
            "by_word": {"sblgnt:n41015040001": [
                {"entity_id": "person:Mary.2", "link_type": "explicit_instances"}]},
        }
    if kind == "ubs_greek":
        return {
            "schema": "bsi.ubs-greek-word-crosswalk.v1",
            "version": "0.1.0",
            "contextual_semantics_independently_verified": False,
            "by_word_id": {"n40001001003": {
                "status": "ubs_entry_only", "entry_ids": ["002427000000000"],
                "provisional_lexid": None, "candidate_lexids": [],
                "evidence_tier": None,
            }},
        }
    return {
        "format": "bsi-ubs-hebrew-lexical-crosswalk",
        "schema_version": 1,
        "by_sdbh": {"006653001001000": ["006653000000000"]},
        "by_strong": {"H7225": ["000001000000000"]},
        "by_macula_word": {"o010010010011": {
            "entry_id": "000001000000000",
            "lemma": "fixture",
            "strong": "7225",
            "lang": "H",
        }},
        "publication": {"version": "1.0.0", "contextual_senses_inferred": 0},
    }


def archive(kind, index=None, *, prefix="", extra=None, broken_manifest=False):
    body = json_bytes(public_index(kind) if index is None else index)
    digest = hashlib.sha256(body).hexdigest()
    manifest = {
        "files": {"index.json": {"sha256": "0" * 64 if broken_manifest else digest,
                                 "bytes": len(body)}},
    }
    values = {prefix + "index.json": body,
              prefix + "manifest.json": json_bytes(manifest)}
    if extra:
        values.update(extra)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zip_out:
        for name, content in values.items():
            zip_out.writestr(name, content)
    return out.getvalue()


def match_lock(kind, raw):
    lock = json.loads((ROOT / "release" / "historical-assets.lock.json")
                      .read_text(encoding="utf-8"))
    copy_lock = copy.deepcopy(lock)
    copy_lock["releases"][kind]["bytes"] = len(raw)
    copy_lock["releases"][kind]["sha256"] = hashlib.sha256(raw).hexdigest()
    return copy_lock


class ExistingV1ArchiveTests(unittest.TestCase):
    def test_approved_public_shapes_are_readable_without_an_application(self):
        for kind in inspect.PUBLIC_SHAPES:
            with self.subTest(kind=kind):
                prefix = "BSI-Archived/" if kind != "ubs_greek" else ""
                payload = archive(kind, prefix=prefix)
                receipt = inspect.inspect(kind, payload, match_lock(kind, payload))
                self.assertEqual(receipt["kind"], kind)
                self.assertEqual(receipt["lookup_records"], 1)
                self.assertEqual(receipt["archive_prefix"], prefix)
                self.assertTrue(receipt["local_byte_integrity_verified"])
                self.assertFalse(receipt["bible_app_modified"])
                self.assertFalse(receipt["new_release_created"])

    def test_changed_archive_bytes_and_wrong_edition_hash_fail_closed(self):
        payload = archive("ubs_greek")
        lock = match_lock("ubs_greek", payload)
        with self.assertRaisesRegex(ValueError, "release bytes differ"):
            inspect.inspect("ubs_greek", payload + b"tamper", lock)
        with self.assertRaisesRegex(ValueError, "release bytes differ"):
            inspect.inspect("ubs_hebrew", payload, lock)

    def test_missing_manifest_and_unsafe_zip_path_are_rejected(self):
        for name in ("../index.json", "a/../../index.json", "/index.json",
                     "a\\index.json"):
            raw = archive("ubs_greek", extra={name: b"bad"})
            with self.subTest(name=name), self.assertRaisesRegex(
                    ValueError, "Unsafe"):
                inspect.inspect("ubs_greek", raw, match_lock("ubs_greek", raw))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive_file:
            archive_file.writestr("index.json", json_bytes(public_index("ubs_greek")))
        raw = buf.getvalue()
        with self.assertRaisesRegex(ValueError, "manifest.json"):
            inspect.inspect("ubs_greek", raw, match_lock("ubs_greek", raw))

    def test_manifest_cannot_falsely_attest_index_bytes(self):
        raw = archive("entities", broken_manifest=True)
        with self.assertRaisesRegex(ValueError, "receipt mismatch"):
            inspect.inspect("entities", raw, match_lock("entities", raw))

    def test_duplicate_keys_in_index_do_not_overwrite_public_semantics(self):
        index = json_bytes(public_index("ubs_greek")).decode()
        tampered = index.replace('"version": "0.1.0"', '"version": "0.1.0", "version": "0.2.0"')
        self.assertIn('"version": "0.2.0"', tampered)
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as z:
            z.writestr("index.json", tampered)
            z.writestr("manifest.json", "{}")
        raw = out.getvalue()
        with self.assertRaisesRegex(ValueError, "Duplicate archive JSON field"):
            inspect.inspect("ubs_greek", raw, match_lock("ubs_greek", raw))

    def test_incompatible_kind_and_contextual_semantics_are_rejected(self):
        greek = public_index("ubs_greek")
        greek["contextual_semantics_independently_verified"] = True
        raw = archive("ubs_greek", greek)
        with self.assertRaisesRegex(ValueError, "falsely approves"):
            inspect.inspect("ubs_greek", raw, match_lock("ubs_greek", raw))
        hebrew = public_index("ubs_hebrew")
        hebrew["publication"]["contextual_senses_inferred"] = 1
        raw = archive("ubs_hebrew", hebrew)
        with self.assertRaisesRegex(ValueError, "sense-approval boundary"):
            inspect.inspect("ubs_hebrew", raw, match_lock("ubs_hebrew", raw))

    def test_restricted_entity_entry_cannot_appear_even_in_fake_valid_zip(self):
        ent = public_index("entities")
        ent["entities"].append({"id": "keyterm:Fake", "kind": "keyterm"})
        raw = archive("entities", ent)
        with self.assertRaisesRegex(ValueError, "restricted Key Terms"):
            inspect.inspect("entities", raw, match_lock("entities", raw))

    def test_restricted_or_malformed_reverse_entity_candidates_are_refused(self):
        variants = [
            [{"entity_id": "keyterm:Private", "link_type": "explicit_instances"}],
            [{"entity_id": None, "link_type": "explicit_instances"}],
            ["unstructured-candidate"],
        ]
        for candidates in variants:
            entity = public_index("entities")
            entity["by_word"]["sblgnt:n41015040001"] = candidates
            raw = archive("entities", entity)
            with self.subTest(candidates=candidates), self.assertRaisesRegex(
                    ValueError, "Restricted or malformed entity reverse candidate"):
                inspect.inspect("entities", raw, match_lock("entities", raw))

    def test_entity_list_and_reverse_map_require_structured_records(self):
        for invalid in ("unknown", [], 42):
            entity = public_index("entities")
            entity["entities"][0] = invalid
            raw = archive("entities", entity)
            with self.subTest(invalid=invalid), self.assertRaisesRegex(
                    ValueError, "malformed entities"):
                inspect.inspect("entities", raw, match_lock("entities", raw))
        entity = public_index("entities")
        entity["by_word"]["sblgnt:n41015040001"] = "not a list"
        raw = archive("entities", entity)
        with self.assertRaisesRegex(ValueError, "Malformed published entity reverse lookup"):
            inspect.inspect("entities", raw, match_lock("entities", raw))

    def test_hebrew_published_type_confusions_fail_closed(self):
        for key, replacement in (
            ("schema_version", True),
            ("schema_version", 1.0),
            ("publication", None),
            ("publication", []),
        ):
            hebrew = public_index("ubs_hebrew")
            hebrew[key] = replacement
            raw = archive("ubs_hebrew", hebrew)
            with self.subTest(key=key, replacement=replacement), self.assertRaisesRegex(
                    ValueError, "sense-approval boundary"):
                inspect.inspect("ubs_hebrew", raw, match_lock("ubs_hebrew", raw))
        hebrew = public_index("ubs_hebrew")
        hebrew["publication"]["contextual_senses_inferred"] = False
        raw = archive("ubs_hebrew", hebrew)
        with self.assertRaisesRegex(ValueError, "sense-approval boundary"):
            inspect.inspect("ubs_hebrew", raw, match_lock("ubs_hebrew", raw))

    def test_real_historical_release_lock_stays_three_kinds(self):
        lock = json.loads((ROOT / "release" / "historical-assets.lock.json")
                          .read_text(encoding="utf-8"))
        inspect.historical.verify_lock(lock)
        self.assertEqual(set(lock["releases"]), set(inspect.PUBLIC_SHAPES))
        self.assertEqual(
            {key: row["tag"] for key, row in lock["releases"].items()},
            {"entities": "bsi-v0.1.0",
             "ubs_greek": "bsi-ubs-greek-v0.1.0",
             "ubs_hebrew": "bsi-ubs-hebrew-v1.0.0"},
        )


if __name__ == "__main__":
    unittest.main()
