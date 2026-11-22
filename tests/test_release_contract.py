"""No BRSI working source input can be misrepresented as an approved release."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_release_contract", ROOT / "scripts" / "release_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
LOCK = json.loads((ROOT / "data/source.lock.json").read_text(encoding="utf-8"))
REV = "a" * 40


def tiny_entity() -> bytes:
    return contract.canonical_json({
        "schema_version": 1,
        "distribution_profile": {
            "name": "bsi-v0.1-without-keyterms",
            "excluded_kinds": ["keyterm"],
        },
        "provenance": {"source_snapshot_sha256": LOCK["source_snapshot_sha256"]},
        "entities": [{
            "id": "person:Mary.2", "kind": "person",
            "source_id": "person:Mary.2",
            "review_status": "source_unreviewed",
        }],
        "by_word": {},
    })


class ArtifactContractTests(unittest.TestCase):
    def test_entity_local_receipt_is_reproducible_and_unapproved(self):
        raw = tiny_entity()
        manifest = contract.make_local_receipt("entities", raw, REV, LOCK)
        self.assertEqual(contract.canonical_json(manifest),
                         contract.canonical_json(contract.make_local_receipt(
                             "entities", raw, REV, LOCK)))
        self.assertEqual(manifest["artifact"]["bytes"], len(raw))
        self.assertEqual(manifest["artifact"]["sha256"], contract.digest(raw))
        self.assertEqual(manifest["publication"]["status"], "candidate_unapproved")
        self.assertEqual(manifest["publication"]["approved"], False)
        self.assertEqual(manifest["rights"]["redistribution_cleared"], False)
        self.assertIsNone(contract.verify_bytes(manifest, raw))
        with self.assertRaisesRegex(ValueError, "Pinned approved release"):
            contract.verify_bytes(manifest, raw, require_release=True)
        self.assertEqual({x["name"] for x in manifest["source_editions"]},
                         {"ACAI", "MACULA SBLGNT", "MACULA WLC"})

    def test_lexical_baseline_can_only_get_local_integrity_receipt(self):
        for kind, path in (
            ("ubs_greek", "links/dictionaries/ubs-greek/index.json"),
            ("ubs_hebrew", "links/dictionaries/ubs-hebrew/index.json"),
        ):
            with self.subTest(kind=kind):
                raw = (ROOT / path).read_bytes()
                manifest = contract.make_local_receipt(kind, raw, REV, LOCK)
                self.assertEqual(manifest["publication"]["status"], "local_integrity_only")
                self.assertFalse(manifest["publication"]["approved"])
                self.assertEqual(manifest["artifact"]["input_class"],
                                 "checked_in_nonpublic_lexical_baseline")
                self.assertIsNone(contract.verify_bytes(manifest, raw))
                with self.assertRaisesRegex(ValueError, "Pinned approved release"):
                    contract.verify_bytes(manifest, raw, require_release=True)

    def test_malformed_payload_and_keyterms_are_rejected(self):
        for value in (
            {"entities": [{"id": "keyterm:Forbidden"}]},
            {"by_word": {"wlc:o010010010001": [{"entity_id": "keyterm:Hidden"}]}},
        ):
            obj = contract.load_json(tiny_entity())
            obj.update(value)
            with self.assertRaisesRegex(ValueError, "Key Term"):
                contract.make_local_receipt("entities", contract.canonical_json(obj), REV, LOCK)
        obj = contract.load_json(tiny_entity())
        obj["provenance"]["source_snapshot_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "keyterm-free"):
            contract.make_local_receipt("entities", contract.canonical_json(obj), REV, LOCK)
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            contract.load_json(b'{"x":1,"x":2}')

    def test_tampering_or_false_publication_approval_is_rejected(self):
        raw = tiny_entity()
        base = contract.make_local_receipt("entities", raw, REV, LOCK)
        with self.assertRaisesRegex(ValueError, "checksum"):
            contract.verify_bytes(base, raw + b" ")
        changes = [
            ("artifact", "filename", "../unsafe.zip"),
            ("artifact", "bytes", True),
            ("publication", "approved", True),
            ("publication", "tag", "brsi-entities-v1.0.0"),
            ("rights", "redistribution_cleared", True),
            ("artifact", "input_class", "source_reviewed_public_projection"),
            ("publication", "status", "owner_approved_release"),
        ]
        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                test = copy.deepcopy(base)
                test[section][key] = value
                with self.assertRaises(ValueError):
                    contract.validate_manifest(test)
        changed_hash = copy.deepcopy(base)
        changed_hash["artifact"]["sha256"] = "f" * 64
        contract.validate_manifest(changed_hash)  # Well-formed but wrong for the bytes.
        with self.assertRaisesRegex(ValueError, "checksum"):
            contract.verify_bytes(changed_hash, raw)
        with self.assertRaisesRegex(ValueError, "manifest"):
            contract.validate_manifest({**base, "sneaky": True})

    def test_consumer_must_pin_version_checksum_and_producer_commit(self):
        # Simulated future *owner-approved* release metadata only, not a
        # release authorization or a new real release asset.
        payload = b"example-reviewed-public-archive-fixture"
        candidate = contract.make_local_receipt("entities", tiny_entity(), REV, LOCK)
        approved = copy.deepcopy(candidate)
        approved["version"] = "1.0.0"
        approved["artifact"] = {
            "filename": "BRSI-Entities-1.0.0.zip",
            "sha256": contract.digest(payload),
            "bytes": len(payload),
            "input_class": "source_reviewed_public_projection",
        }
        approved["publication"] = {
            "status": "owner_approved_release", "approved": True,
            "tag": "brsi-entities-v1.0.0",
            "repository": contract.REPO,
        }
        approved["rights"]["redistribution_cleared"] = True
        contract.validate_manifest(approved)
        with self.assertRaisesRegex(ValueError, "Pinned approved release"):
            contract.verify_bytes(approved, payload, require_release=True)
        kwargs = dict(
            require_release=True, expected_sha256=contract.digest(payload),
            expected_version="1.0.0", expected_revision=REV,
            expected_tag="brsi-entities-v1.0.0")
        contract.verify_bytes(approved, payload, **kwargs)
        for changed in (
            {"expected_sha256": "f" * 64},
            {"expected_version": "2.0.0"},
            {"expected_revision": "b" * 40},
            {"expected_tag": "brsi-entities-v2.0.0"},
        ):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "pinned"):
                contract.verify_bytes(approved, payload, **{**kwargs, **changed})

    def test_cross_kind_and_bad_source_revision_are_rejected(self):
        entity = contract.make_local_receipt("entities", tiny_entity(), REV, LOCK)
        for kind in ("ubs_greek", "ubs_hebrew"):
            altered = copy.deepcopy(entity)
            altered["kind"] = kind
            with self.assertRaisesRegex(ValueError, "Private baseline"):
                contract.validate_manifest(altered)
        for revision in ("main", "v1.0.0", "", "x" * 40):
            with self.assertRaises(ValueError):
                contract.make_local_receipt("entities", tiny_entity(), revision, LOCK)
        with self.assertRaisesRegex(ValueError, "Duplicate source"):
            altered = copy.deepcopy(entity)
            altered["source_editions"].append(altered["source_editions"][0])
            contract.validate_manifest(altered)


if __name__ == "__main__":
    unittest.main()
