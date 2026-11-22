"""Historical release digests are immutable independent pins, not versions to republish."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_historical_asset", ROOT / "scripts" / "verify_historical_asset.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class HistoricalAssetLockTests(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads(tool.LOCK.read_text(encoding="utf-8"))

    def test_exact_three_original_published_asset_records(self):
        tool.verify_lock(self.lock)
        self.assertEqual(set(self.lock["releases"]),
                         {"entities", "ubs_greek", "ubs_hebrew"})
        for kind, record in self.lock["releases"].items():
            self.assertEqual((record["tag"], record["filename"]), tool.KIND_TAGS[kind])
            self.assertTrue(record["historical"])
            self.assertGreater(record["bytes"], 100000)
            self.assertEqual(len(record["sha256"]), 64)
        self.assertEqual(self.lock["source_repository"], "icfmp/Bible-Resources")

    def test_changed_source_status_or_fake_asset_is_rejected(self):
        changed = copy.deepcopy(self.lock)
        changed["releases"]["entities"]["tag"] = "brsi-entities-v0.1.0"
        with self.assertRaisesRegex(ValueError, "historical"):
            tool.verify_lock(changed)
        changed = copy.deepcopy(self.lock)
        changed["releases"]["ubs_greek"]["historical"] = False
        with self.assertRaisesRegex(ValueError, "historical"):
            tool.verify_lock(changed)
        changed = copy.deepcopy(self.lock)
        changed["releases"]["ubs_hebrew"]["bytes"] = True
        with self.assertRaisesRegex(ValueError, "historical"):
            tool.verify_lock(changed)
        with self.assertRaises(ValueError):
            tool.verify_bytes("ubs_unknown", b"test", self.lock)

    def test_actual_hash_and_byte_length_needed_not_just_manifest(self):
        sample = b"public-archive-fixture-only"
        for kind in tool.KIND_TAGS:
            fake = copy.deepcopy(self.lock)
            fake["releases"][kind]["sha256"] = tool.hashlib.sha256(sample).hexdigest()
            fake["releases"][kind]["bytes"] = len(sample)
            result = tool.verify_bytes(kind, sample, fake)
            self.assertTrue(result["matches_original_gitHub_release"])
            self.assertFalse(result["publication_created"])
            with self.assertRaisesRegex(ValueError, "release bytes differ"):
                tool.verify_bytes(kind, sample + b"x", fake)
            with self.assertRaisesRegex(ValueError, "release bytes differ"):
                tool.verify_bytes(kind, b"x" * len(sample), fake)


if __name__ == "__main__":
    unittest.main()
