#!/usr/bin/env python3
"""Check BSI workspace partition and future crosswalk contract without network."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class WorkspaceTests(unittest.TestCase):
    def test_partition_and_immutable_source_lock(self):
        lock = json.loads((ROOT / "data" / "source.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["source_records_expected"], 6644)
        self.assertEqual(len(lock["source_snapshot_sha256"]), 64)
        self.assertEqual(len(lock["source_commit"]), 40)
        self.assertTrue((ROOT / "data" / "entities").is_dir())
        self.assertTrue((ROOT / "data" / "migration" / "acai-baseline-materialization.json").is_file())
        self.assertTrue((ROOT / "scripts" / "build_native_index.py").is_file())
        for sub in ("work", "links/dictionaries", "links/encyclopedias"):
            self.assertTrue((ROOT / sub / "README.md").is_file(), sub)
        self.assertTrue((ROOT / "scripts" / "compile_index.py").is_file())
        self.assertTrue((ROOT / "data" / "editorial-decisions.json").is_file())

    def test_source_pinned_lexical_workflows_never_publish_ci_evidence(self):
        for workflow in ("bsi-ubs-greek.yml", "bsi-ubs-hebrew.yml"):
            path = ROOT / ".github" / "workflows" / workflow
            self.assertTrue(path.exists(), workflow)
            contents = path.read_text(encoding="utf-8")
            self.assertNotIn("actions/upload-artifact", contents, workflow)
            self.assertNotIn("gh release create", contents, workflow)
            self.assertNotIn("publish_private_work_snapshot.sh", contents, workflow)
            self.assertNotIn("icfmp/ACAI", contents, workflow)

    def test_current_docs_and_scripts_have_no_removed_monorepo_root(self):
        # The historical V0_1/RELEASE_READINESS notes intentionally retain
        # exact old commands and tag URLs as provenance. Current entrypoints
        # must never lead a contributor to the removed workspace.
        current_docs = (
            "README.md",
            "docs/README.md", "docs/EDITING_ENTITIES.md",
            "docs/LOCALIZATION_REVIEW.md", "docs/RIGHTS_AND_INTEGRITY.md",
            "docs/RELEASE_CONTRACT.md", "docs/ROADMAP.md",
            "docs/SOURCE_REFERENCE_SEMANTICS.md",
            "docs/FAMILY_RELATION_REVIEW.md",
            "scripts/README.md", "tests/README.md",
            "links/README.md", "links/dictionaries/README.md",
            "links/dictionaries/ubs-greek/README.md",
            "links/dictionaries/ubs-greek/PUBLIC_RELEASE_NOTES.md",
            "links/dictionaries/ubs-hebrew/README.md",
            "links/encyclopedias/README.md",
            "sources/README.md", "work/README.md",
        )
        retired = (
            "bible-semantic-index/scripts/",
            "bible-semantic-index/tests/",
            "bible-semantic-index/links/",
            "bible-semantic-index/data/",
            "Bible-Resources/tree/main/entity-index/",
            "Bible-Resources/tree/main/bible-semantic-index/",
            ".github/workflows/entity-index.yml",
        )
        for path in (*[ROOT / p for p in current_docs],
                     *sorted((ROOT / "scripts").glob("*.py"))):
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertTrue(path.is_file())
                data = path.read_text(encoding="utf-8")
                for old in retired:
                    self.assertNotIn(old, data, (path, old))

    def test_v1_release_manifest_is_source_scoped(self):
        schema = json.loads((ROOT / "release" / "manifest.schema.json")
                            .read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        required = set(schema["required"])
        self.assertEqual(required, set(schema["properties"]))
        self.assertEqual(schema["properties"]["contract"]["const"],
                         "brsi.artifact.v1")
        self.assertEqual(schema["properties"]["kind"]["enum"],
                         ["entities", "ubs_greek", "ubs_hebrew"])
        self.assertEqual(schema["properties"]["rights"]["properties"]
                         ["redistribution_cleared"]["type"], "boolean")

    def test_crosswalk_schema_is_narrow_and_review_based(self):
        schema = json.loads((ROOT / "links" / "schema.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertFalse(schema["additionalProperties"])
        link = schema["properties"]["links"]["items"]
        self.assertFalse(link["additionalProperties"])
        self.assertEqual(link["properties"]["review_status"]["const"], "reviewed")
        self.assertIn("evidence", link["required"])
        self.assertIn("entry_id", link["required"])
        self.assertNotIn("description", link["properties"])
        self.assertNotIn("article", link["properties"])

if __name__ == "__main__":
    unittest.main()
