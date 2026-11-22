"""Integrity receipts are complete, byte-based and deterministic."""
from __future__ import annotations
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "integrity_receipt", ROOT / "scripts" / "write_integrity_receipt.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReceiptTests(unittest.TestCase):
    def test_byte_fingerprints_and_stable_order(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, b = root / "a.json", root / "b.json"
            a.write_bytes(b"{}\n")
            b.write_bytes(b"\x00\xff")
            actual = module.receipt({"greek": b, "entity": a})
            self.assertEqual(list(actual["files"]), ["entity", "greek"])
            self.assertEqual(actual["scope"], "local_build_file_integrity_only")
            self.assertEqual(actual["files"]["entity"]["sha256"],
                             hashlib.sha256(b"{}\n").hexdigest())
            self.assertEqual(actual["files"]["greek"]["bytes"], 2)
            self.assertEqual(actual, module.receipt({"entity": a, "greek": b}))
            b.write_bytes(b"\x00\xfe")
            self.assertNotEqual(actual, module.receipt({"entity": a, "greek": b}))

    def test_missing_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                module.receipt({"entity": Path(folder) / "missing.json"})
        with self.assertRaises(ValueError):
            module.receipt({})


if __name__ == "__main__":
    unittest.main()
