"""Reject suffix additions that borrow owners, invent evidence, or lose old paths."""

import copy
import unittest

from doeda_suffix_audit import FIXTURE
from doeda_suffix_diagnostics import (
    SuffixAudit,
    attributable,
    owned_derivation,
    validate_components,
)
from doeda_suffix_regressions import effective_formations
from lexical_nada_audit import read
from lexical_nada_compare import canon


class Attribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.formations = {p["head"]: p for p in effective_formations()}
        source = read(FIXTURE)
        cls.parent = next(
            a
            for a in source["before_case_words"]["속된"]["analyses"]
            if a["lemmas"] == [{"text": "속되다", "kind": "predicate"}]
        )
        cls.order = [{"lemma": 0}, {"morpheme": 0}]
        cls.added = copy.deepcopy(cls.parent)
        cls.added["lemmas"] = [{"text": "속", "kind": "root"}]
        cls.added["morphemes"].insert(0, {"form": "되다", "kind": "suffix"})
        cls.added["rules"] = sorted(
            set(cls.parent["rules"] + ["suffix.adjective.doeda"])
        )
        cls.components = {canon(cls.parent): cls.order}

    def test_corrected_bound_root_is_attributed_to_original_whole_owner(self):
        attributable([self.parent], self.added, self.components, self.formations)

    def test_new_filtered_match_uses_original_raw_parent(self):
        before = {
            "normalized": "속된",
            "analyses": [],
            "dictionary": {"readings": [], "lemmas": []},
        }
        after = copy.deepcopy(before)
        after["analyses"] = [self.added]
        after["dictionary"]["readings"] = [{"status": "unknown"}]
        raw = {"속된": {"analyses": [self.parent]}}
        self.assertEqual(
            SuffixAudit(self.components, original_words=raw).word(before, after),
            [self.added],
        )

    def test_spelling_homonym_role_cannot_borrow_global_suffix_marker(self):
        mutated = copy.deepcopy(self.added)
        mutated["lemmas"][0]["kind"] = "nominal"
        with self.assertRaises(AssertionError):
            attributable([self.parent], mutated, self.components, self.formations)

    def test_wrong_suffix_index_unlisted_base_and_lost_original_owner_fail(self):
        for kind in ("index", "base", "owner", "no_order"):
            with self.subTest(kind=kind):
                mutated = copy.deepcopy(self.added)
                parent = copy.deepcopy(self.parent)
                order = self.order
                if kind == "index":
                    mutated["morphemes"].reverse()
                elif kind == "base":
                    mutated["lemmas"][0]["text"] = "아무"
                elif kind == "owner":
                    parent["lemmas"][0]["kind"] = "nominal"
                else:
                    order = None
                with self.assertRaises(AssertionError):
                    attributable(
                        [parent], mutated, {canon(parent): order}, self.formations
                    )

    def test_invented_rules_and_spelling_evidence_are_rejected(self):
        for field in ("rules", "spelling_paths"):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.added)
                if field == "rules":
                    mutated["rules"] = sorted([*mutated["rules"], "invented"])
                else:
                    mutated["spelling_paths"] = [
                        [{"class": "written_vowel_eo", "morpheme_index": 1}]
                    ]
                with self.assertRaises(AssertionError):
                    attributable(
                        [self.parent], mutated, self.components, self.formations
                    )

    def test_malformed_parent_order_is_rejected(self):
        for order in (
            [{"lemma": 0}, {"morpheme": 1}],
            [{"lemma": 0}, {"lemma": 0}, {"morpheme": 0}],
        ):
            with self.subTest(order=order), self.assertRaises(AssertionError):
                validate_components({canon(self.parent): order}, [self.parent])

    def test_original_candidate_loss_and_native_assessment_change_are_rejected(self):
        before = {
            "normalized": "속된",
            "analyses": [self.parent],
            "dictionary": {"readings": [{"status": "compatible"}], "lemmas": []},
        }
        components = self.components
        for kind in ("candidate", "native"):
            with self.subTest(kind=kind):
                after = copy.deepcopy(before)
                if kind == "candidate":
                    after["analyses"] = [self.added]
                else:
                    after["dictionary"]["readings"][0]["status"] = "unknown"
                with self.assertRaises(AssertionError):
                    SuffixAudit(components).word(before, after)

    def test_suffix_index_shift_preserves_a_later_owners_recovery(self):
        parent = copy.deepcopy(self.parent)
        parent["lemmas"].append({"text": "이다", "kind": "copula"})
        parent["morphemes"] = [
            {"form": "음", "kind": "ending"},
            {"form": "어", "kind": "ending"},
        ]
        parent["spelling_paths"] = [
            [{"class": "written_vowel_eo", "morpheme_index": 1}]
        ]
        order = [{"lemma": 0}, {"morpheme": 0}, {"lemma": 1}, {"morpheme": 1}]
        added = copy.deepcopy(parent)
        added["lemmas"][0] = {"text": "속", "kind": "root"}
        added["morphemes"].insert(0, {"form": "되다", "kind": "suffix"})
        derived = owned_derivation(parent, added, order, self.formations)
        self.assertEqual(derived["spelling_paths"][0][0]["morpheme_index"], 2)

    def test_original_native_slot_order_cannot_be_reversed(self):
        identity = {
            "lemmas": [{"text": "속된", "kind": "unclassified"}],
            "morphemes": [],
            "rules": ["identity"],
            "unchanged": True,
        }
        before = {
            "normalized": "속된",
            "analyses": [self.parent, identity],
            "dictionary": {
                "readings": [{"status": "compatible"}, {"status": "unknown"}],
                "lemmas": [
                    {"lemma": self.parent["lemmas"][0], "entries": []},
                    {"lemma": identity["lemmas"][0], "entries": []},
                ],
            },
        }
        after = copy.deepcopy(before)
        after["dictionary"]["lemmas"].reverse()
        with self.assertRaises(AssertionError):
            SuffixAudit(self.components).word(before, after)


if __name__ == "__main__":
    unittest.main()
