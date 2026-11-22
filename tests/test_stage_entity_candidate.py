"""Stage deterministic native-only archive; source rights remain unapproved."""
from __future__ import annotations

import copy
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_entity_zip_candidate", ROOT / "scripts" / "stage_entity_candidate.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
LOCK = json.loads((ROOT / "data/source.lock.json").read_text(encoding="utf-8"))
COMMIT = "e" * 40


def minimal_index() -> bytes:
    return stage.contract.canonical_json({
        "schema_version": 1,
        "distribution_profile": {
            "name": "bsi-v0.1-without-keyterms",
            "excluded_kinds": ["keyterm"], "excluded_entity_count": 868,
        },
        "provenance": {"source_snapshot_sha256": LOCK["source_snapshot_sha256"]},
        "entities": [{
            "id": "person:Mary.2", "kind": "person",
            "source_id": "person:Mary.2",
            "review_status": "source_unreviewed",
            "occurrences": {}, "references": ["41015040"],
        }],
        "by_word": {},
    })


class LocalEntityCandidateTests(unittest.TestCase):
    def test_deterministic_archive_and_receipt(self):
        raw = minimal_index()
        first, one = stage.make_candidate(raw, LOCK, COMMIT)
        second, two = stage.make_candidate(raw, LOCK, COMMIT)
        self.assertEqual(first, second)
        self.assertEqual(one, two)
        self.assertEqual(one["artifact"]["sha256"], stage.contract.digest(first))
        self.assertEqual(one["artifact"]["bytes"], len(first))
        self.assertFalse(one["publication"]["approved"])
        self.assertFalse(one["rights"]["redistribution_cleared"])
        self.assertEqual(one["artifact"]["input_class"], "nonpublishing_entity_zip_candidate")
        self.assertEqual(one["publication"]["status"], "candidate_unapproved")
        manifest = stage.verify_candidate(first, one)
        self.assertEqual(manifest["publication"]["status"], "candidate_unapproved")
        self.assertEqual(set(manifest["files"]), stage.CONTENTS - {"manifest.json"})
        self.assertEqual(manifest["source_editions"], one["source_editions"])
        with zipfile.ZipFile(io.BytesIO(first)) as z:
            self.assertEqual(z.read(stage.PREFIX + "index.json"), raw)
            self.assertEqual(z.read(stage.PREFIX + "source.lock.json"),
                             stage.contract.canonical_json(LOCK))
            self.assertNotIn("labels-en.json", " ".join(z.namelist()))

    def test_checksum_and_publication_bypass_fail_closed(self):
        raw, receipt = stage.make_candidate(minimal_index(), LOCK, COMMIT)
        changed = bytearray(raw)
        changed[-8] ^= 1
        with self.assertRaises(ValueError):
            stage.verify_candidate(bytes(changed), receipt)
        future = copy.deepcopy(receipt)
        future["publication"] = {
            "status": "owner_approved_release",
            "approved": True, "tag": "brsi-entities-v1.0.0",
            "repository": stage.contract.REPO,
        }
        with self.assertRaises(ValueError):
            stage.verify_candidate(raw, future)
        with self.assertRaisesRegex(ValueError, "Pinned approved release"):
            stage.contract.verify_bytes(receipt, raw, require_release=True)

    def test_forbidden_content_and_baseline_lexical_inputs(self):
        for bad in ("keyterm:Secret", "person:Mary.2"):
            index = stage.contract.load_json(minimal_index())
            if bad.startswith("keyterm:"):
                index["entities"].append({
                    "id": bad, "kind": "keyterm", "source_id": bad,
                })
                with self.assertRaisesRegex(ValueError, "Key Term"):
                    stage.make_candidate(stage.contract.canonical_json(index), LOCK, COMMIT)
            else:
                index["distribution_profile"]["excluded_kinds"] = []
                with self.assertRaisesRegex(ValueError, "keyterm-free"):
                    stage.make_candidate(stage.contract.canonical_json(index), LOCK, COMMIT)
        for kind in ("ubs-greek", "ubs-hebrew"):
            lexical = (ROOT / "links/dictionaries" / kind / "index.json").read_bytes()
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "keyterm-free"):
                stage.make_candidate(lexical, LOCK, COMMIT)

    def test_manifest_content_tampering_rejected_even_if_zip_sha_recalculated(self):
        original_zip, receipt = stage.make_candidate(minimal_index(), LOCK, COMMIT)
        with zipfile.ZipFile(io.BytesIO(original_zip)) as old:
            files = {i.filename: old.read(i.filename) for i in old.infolist()}
        original_internal = stage.contract.load_json(files[stage.PREFIX + "manifest.json"])
        original_internal["files"]["index.json"]["sha256"] = "f" * 64
        files[stage.PREFIX + "manifest.json"] = stage.contract.canonical_json(original_internal)
        buff = io.BytesIO()
        with zipfile.ZipFile(buff, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as zip_out:
            for path, blob in sorted(files.items()):
                info = zipfile.ZipInfo(path, date_time=stage.ZIP_DATE)
                info.create_system = 3
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zip_out.writestr(info, blob, compress_type=zipfile.ZIP_DEFLATED,
                                 compresslevel=9)
        modified = buff.getvalue()
        fake_receipt = copy.deepcopy(receipt)
        fake_receipt["artifact"]["sha256"] = stage.contract.digest(modified)
        fake_receipt["artifact"]["bytes"] = len(modified)
        with self.assertRaisesRegex(ValueError, "internal candidate manifest"):
            stage.verify_candidate(modified, fake_receipt)

    def test_unsafe_inputs_or_source_revision_fail(self):
        original = minimal_index()
        with self.assertRaisesRegex(ValueError, "Git commit"):
            stage.make_candidate(original, LOCK, "main")
        corrupted_lock = copy.deepcopy(LOCK)
        corrupted_lock["source_snapshot_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "keyterm-free"):
            stage.make_candidate(original, corrupted_lock, COMMIT)
        with self.assertRaisesRegex(ValueError, "canonical"):
            stage.make_candidate(original.replace(b'":', b'": '), LOCK, COMMIT)


if __name__ == "__main__":
    unittest.main()
