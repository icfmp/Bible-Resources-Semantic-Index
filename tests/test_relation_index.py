"""A source-field relation lookup must never become invented biblical fact."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "brsi_relation_projection", ROOT / "scripts" / "build_relation_index.py")
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


class RelationIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        (self.data / "entities" / "people").mkdir(parents=True)
        (self.data / "entities" / "places").mkdir(parents=True)
        (self.data / "entities" / "groups").mkdir(parents=True)
        (self.data / "quarantined" / "people").mkdir(parents=True)
        (self.data / "source.lock.json").write_text(json.dumps({
            "source_repository": "https://example.invalid/source",
            "source_commit": "c" * 40,
            "source_snapshot_sha256": "a" * 64,
            "source_license": "CC BY-SA 4.0",
        }), encoding="utf-8")

    def record(self, category, name, **relations):
        identity = {"people": "person", "places": "place", "groups": "group"}[category] + ":" + name
        data = {
            "id": identity,
            "type": category[:-1],
            "bsi": {
                "source_id": identity,
                "canonical_id": identity,
                "source_sha256": "f" * 64,
            },
            **relations,
        }
        path = self.data / "entities" / category / (name + ".json")
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_forward_and_reverse_preserve_direction_and_exact_paths(self):
        person = self.record("people", "A", father="person:B",
                             offspring=["person:C", "group:G"],
                             partners=["person:C"],
                             unclassified_relation="person:B",
                             group_origin="person:B; person:C")
        for name in ("B", "C"):
            self.record("people", name)
        self.record("groups", "G")
        before = person.read_bytes()
        graph = projection.build(self.data)
        self.assertEqual(person.read_bytes(), before)
        self.assertFalse(graph["publication_approved"])
        self.assertEqual(graph["counts"]["indexed_claims"], 7)
        self.assertEqual(graph["counts"]["withheld_unclassified"], 1)
        self.assertEqual(graph["counts"]["source_unreviewed"], 6)
        self.assertEqual(graph["counts"]["unclassified_by_field"],
                         {"unclassified_relation": 1})
        self.assertEqual(graph["counts"]["by_source_field"]["group_origin"], 2)
        self.assertEqual(len(graph["by_source"]["person:A"]), 7)
        self.assertEqual(len(graph["by_target"]["person:B"]), 3)
        self.assertNotIn("person:A", graph["by_target"])
        links = {tuple(c["evidence"]["json_path"]): c for c in graph["claims"]}
        self.assertEqual(links[("father",)]["predicate"], "reported_father")
        self.assertEqual(links[("offspring", 1)]["target_id"], "group:G")
        self.assertEqual(links[("partners", 0)]["predicate"], "reported_partner")
        self.assertEqual(links[("group_origin", 1)]["target_id"], "person:C")
        self.assertEqual(links[("unclassified_relation",)]["review_status"],
                         "withheld_unclassified")
        self.assertIsNone(links[("unclassified_relation",)]["predicate"])
        self.assertEqual(links[("father",)]["evidence"]["evidence_scope"],
                         "inherited_record_field_only")
        self.assertEqual(projection.canonical_bytes(graph),
                         projection.canonical_bytes(projection.build(self.data)))

    def test_ambiguous_identity_links_are_withheld_not_merged(self):
        self.record("people", "A", possibly_same_as=["person:B"],
                    referred_to_as=["person:B"])
        self.record("people", "B")
        graph = projection.build(self.data)
        self.assertEqual(graph["counts"]["withheld_identity_or_alias"], 2)
        self.assertEqual(graph["counts"]["source_unreviewed"], 0)
        self.assertEqual(graph["counts"]["withheld_identity_or_alias_by_field"], {
            "possibly_same_as": 1, "referred_to_as": 1,
        })
        self.assertEqual(len(graph["by_target"]["person:B"]), 2)
        for claim in graph["claims"]:
            self.assertEqual(claim["review_status"], "withheld_identity_or_alias")
            self.assertIsNone(claim["predicate"])
            self.assertNotEqual(claim["source_id"], claim["target_id"])

    def test_geographic_association_keeps_original_direction(self):
        self.record("places", "A", associated_places=["place:B"],
                    nearby_places=["place:B"], related_places=["place:B"],
                    tribal_area=["place:B"])
        self.record("places", "B")
        graph = projection.build(self.data)
        self.assertEqual(
            {c["predicate"] for c in graph["claims"]},
            {"reported_associated_place", "reported_nearby_place",
             "reported_related_place", "reported_tribal_area"})
        self.assertEqual(len(graph["by_target"]["place:B"]), 4)
        self.assertNotIn("place:B", graph["by_source"])

    def test_disagreed_parent_claims_are_both_withheld_without_repair(self):
        self.record("people", "A", gender="male", offspring=["person:C"])
        self.record("people", "B", gender="male")
        self.record("people", "C", father="person:B")
        graph = projection.build(self.data)
        self.assertEqual(graph["counts"]["inverse_disagreement_cases"], 1)
        self.assertEqual(graph["counts"]["withheld_inverse_disagreement"], 2)
        self.assertEqual(graph["counts"]["withheld_inverse_disagreement_by_field"],
                         {"father": 1, "offspring": 1})
        self.assertEqual(
            {(row["source_id"], row["source_field"], row["target_id"])
             for row in graph["claims"]
             if row["review_status"] == "withheld_inverse_disagreement"},
            {("person:A", "offspring", "person:C"),
             ("person:C", "father", "person:B")})
        self.assertEqual(len(graph["by_target"]["person:B"]), 1)
        self.assertEqual(len(graph["by_target"]["person:C"]), 1)

    def test_matching_inverse_claims_stay_unreviewed_not_approved(self):
        self.record("people", "A", gender="male", offspring=["person:C"])
        self.record("people", "C", father="person:A")
        graph = projection.build(self.data)
        self.assertEqual(graph["counts"]["inverse_disagreement_cases"], 0)
        self.assertEqual(graph["counts"]["withheld_inverse_disagreement"], 0)
        self.assertEqual({c["review_status"] for c in graph["claims"]},
                         {"source_unreviewed"})

    def test_missing_and_quarantined_targets_fail_closed(self):
        self.record("people", "A", mother="person:Absent")
        with self.assertRaisesRegex(ValueError, "stale, quarantined or unresolved"):
            projection.build(self.data)
        self.record("people", "Absent")
        self.assertEqual(projection.build(self.data)["counts"]["indexed_claims"], 1)
        (self.data / "entities" / "people" / "Absent.json").rename(
            self.data / "quarantined" / "people" / "Absent.json")
        with self.assertRaisesRegex(ValueError, "stale, quarantined or unresolved"):
            projection.build(self.data)

    def test_excluded_keyterms_never_appear_in_output(self):
        self.record("people", "A", tribe="keyterm:RestrictedWord")
        self.record("people", "B")
        graph = projection.build(self.data)
        self.assertEqual(graph["counts"]["excluded_restricted_keyterm_claims"], 1)
        self.assertEqual(graph["counts"]["indexed_claims"], 0)
        self.assertNotIn("RestrictedWord", json.dumps(graph))

    def test_source_fields_cannot_be_verse_or_word_evidence(self):
        self.record("people", "A", siblings=["person:B"],
                    references=["01001001"],
                    explicit_instances={"WLC": [["o010010010011"]]})
        self.record("people", "B")
        graph = projection.build(self.data)
        self.assertEqual(len(graph["claims"]), 1)
        self.assertEqual(graph["claims"][0]["source_field"], "siblings")
        self.assertNotIn("references", graph["claims"][0]["evidence"])
        self.assertNotIn("original_word_ids", graph["claims"][0]["evidence"])

    def test_schema_is_versioned_and_forbids_public_approval(self):
        schema = json.loads(
            (ROOT / "relations" / "schema.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["publication_approved"], {"const": False})
        self.assertFalse(schema["additionalProperties"])
        claim = schema["properties"]["claims"]["items"]
        self.assertFalse(claim["additionalProperties"])
        self.assertEqual(set(projection.SOURCE_PREDICATES.values()),
                         set(claim["properties"]["predicate"]["oneOf"][0]["enum"]))

    def test_real_source_examples_do_not_prove_genealogical_agreement(self):
        graph = projection.build(ROOT / "data")
        self.assertGreaterEqual(graph["counts"]["indexed_claims"], 15000)
        self.assertEqual(
            graph["counts"]["indexed_claims"] +
            graph["counts"]["excluded_restricted_keyterm_claims"],
            graph["counts"]["source_relationships"])
        def claims_for(source, field, target):
            return [c for c in graph["claims"] if c["source_id"] == source
                    and c["source_field"] == field and c["target_id"] == target]
        self.assertEqual(len(claims_for("person:Lot", "father", "person:Haran")), 1)
        self.assertEqual(
            len(claims_for("place:Gadara", "subregion_of", "place:Decapolis")), 1)
        contested = claims_for("group:Ludim", "group_origin", "person:Lud")
        self.assertEqual(len(contested), 1)
        self.assertEqual(contested[0]["review_status"], "source_unreviewed")
        self.assertNotIn("verse_ids", contested[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
