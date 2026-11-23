"""Exercise real native BRSI words, false pairs, omissions, ambiguity and absences."""
from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

native=load("bsi_native_real_word_integration","build_native_index.py")
resolver_module=load("bsi_resolve_real_word_integration","resolve.py")

class RealPinnedSourceResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=native.build(ROOT/"data")
        cls.resolver=resolver_module.EntityResolver(cls.index)
        cls.editions=cls.index["provenance"]["source_editions"]

    def query(self,corpus,word,reader=True,edition=None):
        func=(self.resolver.resolve_for_reader if reader else self.resolver.resolve)
        return func(corpus=corpus,edition=edition or self.editions[corpus]["edition"],
                    word_id=word,verse_id=word[1:9])

    def test_actual_tribal_places_are_not_cross_propagated_by_equal_names(self):
        cases=[
            ("wlc","o060190290032","place:Ramah.6"),
            ("wlc","o060190360023","place:Ramah.3"),
            ("wlc","o060180250023","place:Ramah.4"),
            ("wlc","o240310150052","place:Ramah.4"),
            ("sblgnt","n40002018003","place:Ramah.4"),
            ("sblgnt","n44016040009","person:Lydia"),
            ("sblgnt","n40017027023","realia:Stater"),
            ("sblgnt","n43004006004","place:JacobsWell"),
            ("wlc","o130020490081","place:Machbenah"),
        ]
        for corpus,word,expected in cases:
            with self.subTest(word=word):
                result=self.query(corpus,word)
                self.assertIn(expected,result["canonical_ids"])
                self.assertTrue(all(x["link_type"]=="explicit_instances"
                                    for x in result["candidates"]))
                self.assertEqual(result["lookup_policy"],"explicit_only")
                self.assertNotIn("person:HusbandOfMary",result["canonical_ids"])
        self.assertNotIn("place:Lydia",
                         self.query("sblgnt","n44016040009")["canonical_ids"])
        self.assertNotIn("place:Ramah.4",
                         self.query("wlc","o060190290032")["canonical_ids"])
        self.assertNotIn("place:Ramah.3",
                         self.query("wlc","o060190290032")["canonical_ids"])

    def test_real_raw_word_ambiguity_remains_multiplicity_not_guess(self):
        by_word=self.index["by_word"]
        entities={x["id"]:x for x in self.index["entities"]}
        ambiguous=[
            (key,hits) for key,hits in by_word.items()
            if len({entities[h["entity_id"]]["canonical_id"] for h in hits})>1
        ]
        self.assertTrue(ambiguous,"A source-sensitive real case is required")
        key,hits=sorted(ambiguous,key=lambda item:item[0])[0]
        corpus,word=key.split(":",1)
        expected={entities[h["entity_id"]]["canonical_id"] for h in hits}
        raw=self.query(corpus,word,reader=False)
        reader=self.query(corpus,word,reader=True)
        self.assertEqual(raw["status"],"ambiguous_source_candidates")
        self.assertEqual(set(raw["canonical_ids"]),expected)
        self.assertTrue(set(reader["canonical_ids"]).issubset(expected))
        self.assertTrue(all(x["link_type"]=="explicit_instances"
                            for x in reader["candidates"]))
        self.assertEqual(self.query(corpus,word,edition="unrelated-edition")
                         ["status"],"incompatible_source_edition")

    def test_actual_only_indirect_word_does_not_identify_an_actor(self):
        possible=[
            (key,hits) for key,hits in self.index["by_word"].items()
            if hits and all(h["link_type"]!="explicit_instances" for h in hits)
        ]
        self.assertTrue(possible)
        key,_=sorted(possible,key=lambda item:item[0])[0]
        corpus,word=key.split(":",1)
        self.assertIn(self.query(corpus,word,reader=False)["status"],
                      {"source_candidate","ambiguous_source_candidates"})
        display=self.query(corpus,word)
        self.assertEqual(display["status"],"no_explicit_entity")
        self.assertEqual(display["canonical_ids"],[])

    def test_actual_pinned_verse_and_original_word_absences_fail_closed(self):
        missing_word=self.index["unattested_source_words"]
        self.assertTrue(missing_word)
        key=sorted(missing_word)[0]
        corpus,word=key.split(":",1)
        self.assertEqual(self.query(corpus,word)["status"],
                         "unattested_source_word_id")
        self.assertNotIn(key,self.index["by_word"])
        missing_verses=self.index["unattested_source_verses"]
        self.assertTrue(missing_verses)
        key=sorted(missing_verses)[0]
        corpus,verse=key.split(":",1)
        spec=self.editions[corpus]
        word=(spec["word_id_prefix"]+verse+
              "0"*(spec["word_id_digits"]-len(verse)))
        result=self.resolver.resolve_for_reader(
            corpus=corpus,edition=spec["edition"],
            word_id=word,verse_id=verse)
        self.assertEqual(result["status"],
                         "verse_not_in_pinned_original_word_inventory")
        self.assertEqual(result["canonical_ids"],[])

if __name__=="__main__":
    unittest.main()
