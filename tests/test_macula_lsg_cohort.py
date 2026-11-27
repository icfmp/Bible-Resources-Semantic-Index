"""Regression coverage for scripts/macula_lsg_cohort.py.

Synthetic only: these tests do not certify biblical editorial decisions.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import macula_lsg_cohort as cohort


class CohortTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = self.root / "sources"
        self.path_patch = patch.object(cohort, "source_paths", self.paths)
        self.sources_patch = patch.object(cohort, "SOURCES", self.sources)
        self.path_patch.start()
        self.sources_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.addCleanup(self.sources_patch.stop)
        self.put(self.sources / "lsg" / "manifest.json", {
            "license": "synthetic", "git_blob": "f" * 40, "commit": "e" * 40, "bytes": 1})
        self.put(self.sources / "macula-hebrew" / "manifest.json", {
            "attribution": "synthetic", "commit": "d" * 40})
        self.chapter(1, {"1": "Un mot.", "2": "Autre mot."}, {
            1: [("a", "noun"), ("b", "particle")],
            2: [("c", "noun"), ("d", "noun")]})
        self.plan = cohort.make_plan(["Gen.1"], {"identity_default": True})
        self.plan_path = self.root / "plan.json"
        self.put(self.plan_path, self.plan)
        self.plan, self.f, self.h, self.routes = cohort.load_plan(self.plan_path)
        self.rows = {"Gen.1.1": "1:2;2~1", "Gen.1.2": "1:1;2:2"}
        self.draft = cohort.draft_envelope(self.plan, self.rows)

    def put(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def paths(self, book, chapter):
        return (self.sources / "lsg" / book / f"{chapter:03d}.json",
                self.sources / "macula-hebrew" / book / f"{chapter:03d}.json")

    def chapter(self, chapter, verses, words):
        f, h = self.paths("Gen", chapter)
        digest = hashlib.sha256("\n".join(verses[v] for v in sorted(verses, key=int)).encode()).hexdigest()
        self.put(f, {"book": "Gen", "chapter": chapter, "verses": verses,
                     "reading_text_sha256": digest})
        self.put(h, {"source_path": f"synthetic/{chapter}.xml", "git_blob": str(chapter) * 40,
                     "words": [[word, f"GEN {chapter}:{v}!{i}", word, word, pos, "X", "H"]
                               for v, ws in words.items() for i, (word, pos) in enumerate(ws, 1)]})

    def delta(self, reviewed, corrections=None, **extra):
        return self.put(self.root / f"delta-{len(list(self.root.glob('delta-*')))}.json",
                        {"schema_version": 1, "plan_sha256": cohort.digest(self.plan),
                         "draft_sha256": cohort.digest(self.draft), "reviewed": reviewed,
                         "corrections": corrections or {}, **extra})

    def overlay(self, *paths):
        return cohort.review_overlay(self.plan, self.draft, paths, self.f, self.h, self.routes)

    def report(self, effective, reviewed, changed):
        return cohort.summary(self.plan, self.draft, effective, reviewed, changed,
                              self.f, self.h, self.routes)

    def test_scopes_and_explicit_routing(self):
        self.assertEqual(cohort.expand_scopes(["Josh.11-12", "Judg.1"]),
                         ["Josh.11", "Josh.12", "Judg.1"])
        with self.assertRaises(ValueError):
            cohort.make_plan(["Gen.1"], {})
        with self.assertRaises(ValueError):
            cohort.expand_scopes(["Gen.1", "Gen.1"])

    def test_no_review_no_ledger(self):
        report, ledgers = self.report(self.rows, set(), set())
        self.assertEqual(report["reviewed"], 0)
        self.assertEqual(report["eligible_chapters"], 0)
        self.assertFalse(ledgers)

    def test_review_delta_keeps_initial_map(self):
        path = self.delta(list(self.rows), {"Gen.1.1": "1:1-2;2~1"})
        effective, reviewed, changed, _ = self.overlay(path)
        self.assertEqual(self.draft["rows"]["Gen.1.1"], "1:2;2~1")
        self.assertEqual(changed, {"Gen.1.1"})
        report, ledgers = self.report(effective, reviewed, changed)
        self.assertEqual(report["eligible_chapters"], 1)
        self.assertEqual(ledgers["Gen.1"]["statistics"]["lexical_content_translation"], 3)
        self.assertEqual(ledgers["Gen.1"]["relations"][0]["french"][1], [1, 2, 3, 6])
        self.assertIn("publication validation pending", ledgers["Gen.1"]["status"])

    def test_amendment_bound_to_effective_map(self):
        a = self.delta(list(self.rows))
        effective, _, _, _ = self.overlay(a)
        b = self.delta(["Gen.1.1"], {"Gen.1.1": "1:1-2;2~1"},
                       amends_effective_sha256=cohort.digest(effective))
        updated, reviewed, changed, _ = self.overlay(a, b)
        self.assertEqual(len(reviewed), 2)
        self.assertEqual(changed, {"Gen.1.1"})
        self.assertEqual(updated["Gen.1.1"]["map"], "1:1-2;2~1")
        with self.assertRaises(ValueError):
            self.overlay(b, a)

    def test_reject_duplicate_and_unreviewed_correction(self):
        with self.assertRaises(ValueError):
            self.overlay(self.delta(["Gen.1.1"], {"Gen.1.2": "1:2;2:1"}))
        a = self.delta(["Gen.1.1"])
        with self.assertRaises(ValueError):
            self.overlay(a, a)

    def test_reject_stale_source_or_draft(self):
        d = self.delta(list(self.rows))
        self.draft = cohort.draft_envelope(self.plan, {**self.rows, "Gen.1.1": "1:1-2;2~1"})
        with self.assertRaises(ValueError):
            self.overlay(d)
        f, _ = self.paths("Gen", 1)
        f.write_text(f.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Pinned projection"):
            cohort.load_plan(self.plan_path)

    def test_bad_ordinal_and_duplicate_relation(self):
        for row in ("3:1", "1:99", "1:1;1:1"):
            with self.assertRaises((ValueError, KeyError)):
                cohort.decode("Gen.1.1", row, self.f, self.h, self.routes)

    def test_omission_is_not_lexical_coverage(self):
        effective = {**self.rows, "Gen.1.2": {"map": "1:1-2", "omissions": [
            {"ordinals": "2", "note": "Synthetic source omission"}]}}
        report, ledgers = self.report(effective, set(self.rows), set())
        chapter = report["chapters"]["Gen.1"]
        self.assertEqual(chapter["unaccounted_hebrew"], [])
        self.assertEqual(chapter["explicit_omissions"], 1)
        self.assertAlmostEqual(chapter["lexical_coverage"], 2 / 3)
        self.assertFalse(ledgers)
        with self.assertRaises(ValueError):
            cohort.decode("Gen.1.2", {"map": "1:1;2:2", "omissions": [
                {"ordinals": "2", "note": "Overlaps"}]}, self.f, self.h, self.routes)

    def test_contextual_not_lexical(self):
        effective = {**self.rows, "Gen.1.2": "1:1;2~2"}
        report, ledgers = self.report(effective, set(self.rows), set())
        self.assertAlmostEqual(report["chapters"]["Gen.1"]["lexical_coverage"], 2 / 3)
        self.assertFalse(ledgers)

    def test_legacy_import_preserves_unresolved(self):
        fp, hp = self.plan["source_pins"]["lsg"]["Gen.1"], self.plan["source_pins"]["macula"]["Gen.1"]
        p = self.put(self.root / "legacy.json", {"chapters": [{
            "scope": "Gen.1", "source_lsg_projection_blob": fp["projection_blob"],
            "source_lsg_sha256": fp["reading_text_sha256"],
            "source_macula_projection_blob": hp["projection_blob"],
            "source_macula_blob": hp["upstream_blob"],
            "rows": {"1": {"french_target": "Gen.1.1", "manual_map": "1:2",
                           "unresolved_hebrew": [2], "note": "Inspect omission"},
                     "2": {"alternatives": [["1:1", 1]]}}}]})
        rows = cohort.legacy_rows([p], self.plan, self.h, self.routes)
        self.assertEqual(set(rows), {"Gen.1.1"})
        self.assertNotIn("omissions", rows["Gen.1.1"])
        self.assertEqual(cohort.decode("Gen.1.1", rows["Gen.1.1"], self.f, self.h, self.routes)[2], {"b"})

    def test_shared_boundary_route(self):
        self.chapter(2, {"1": "Mot."}, {1: [("e", "noun")]})
        # The target inventory must remain complete; an unmapped verse is rejected.
        with self.assertRaisesRegex(ValueError, "inventory"):
            cohort.make_plan(["Gen.1", "Gen.2"], {
                "identity_default": True, "routes": {"Gen.1.2": "Gen.2.1"}})
        self.chapter(1, {"1": "Un mot.", "2": "Autre mot."}, {
            1: [("a", "noun"), ("b", "particle")],
            2: [("c", "noun"), ("d", "noun")],
            3: [("z", "noun")]})
        plan = cohort.make_plan(["Gen.1", "Gen.2"], {
            "identity_default": True, "routes": {"Gen.1.3": "Gen.2.1"}})
        self.assertEqual(plan["targets"]["Gen.1.3"], "Gen.2.1")
        self.assertEqual(plan["targets"]["Gen.2.1"], "Gen.2.1")


if __name__ == "__main__":
    unittest.main()
