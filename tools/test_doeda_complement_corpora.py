"""Regression checks for additive audits without rewriting original gold."""

import unittest
from copy import deepcopy

from doeda_complement_corpora import candidate_changes, gold_changes


class ComplementCorpusAuditTests(unittest.TestCase):
    def setUp(self):
        self.gold = {
            "id": "id:sentence/1",
            "surface": "token",
            "expected": ["a", "b", "c"],
            "matched": False,
            "recovered": 1,
            "recovered_sets": [[0], [1]],
        }
        self.context = {
            self.gold["id"]: {
                "complete_sentence": "original",
                "original_row": ["1", "token"],
            }
        }
        self.old_path = {
            "lemmas": [{"text": "먹다", "kind": "predicate"}],
            "morphemes": [],
            "rules": ["identity"],
            "unchanged": True,
        }
        self.new_path = {
            "lemmas": [
                {"text": "먹다", "kind": "predicate"},
                {"text": "되다", "kind": "predicate"},
            ],
            "morphemes": [{"form": "어도", "kind": "ending"}],
            "rules": ["lexical.doeda.extended"],
            "unchanged": False,
        }
        self.before = {"normalized": "먹어도된다", "analyses": [self.old_path]}
        self.after = {
            "normalized": "먹어도된다",
            "analyses": [self.new_path, self.old_path],
        }

    def test_new_maximal_recovery_can_replace_dominated_sets(self):
        after = dict(self.gold, recovered=2, recovered_sets=[[0, 1]])
        (change,) = gold_changes([self.gold], [after], self.context)
        self.assertEqual(change["before"], self.gold)
        self.assertEqual(change["after"], after)
        self.assertEqual(change["complete_sentence"], "original")

    def test_equal_aggregate_recovery_cannot_hide_lost_group(self):
        after = dict(self.gold, recovered=2, recovered_sets=[[0, 2]])
        with self.assertRaises(AssertionError):
            gold_changes([self.gold], [after], self.context)

    def test_rewriting_gold_or_losing_complete_match_fails(self):
        for after in (
            dict(self.gold, expected=["replacement"]),
            dict(self.gold, surface="replacement"),
        ):
            with self.subTest(after=after), self.assertRaises(AssertionError):
                gold_changes([self.gold], [after], self.context)
        matched = dict(self.gold, matched=True, recovered=3, recovered_sets=[[0, 1, 2]])
        with self.assertRaises(AssertionError):
            gold_changes([matched], [dict(matched, matched=False)], self.context)

    def test_added_candidate_has_stable_individual_identity(self):
        changes = candidate_changes("먹어도된다", self.before, self.after, [])
        self.assertEqual(
            changes, candidate_changes("먹어도된다", self.before, self.after, [])
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["after"], self.new_path)
        self.assertEqual(changes[0]["contextual_verdict"], "unjudged")

    def test_candidate_replacement_and_order_loss_fail(self):
        other = dict(self.old_path, rules=["other"])
        before = dict(self.before, analyses=[self.old_path, other])
        for after in (
            dict(self.after, analyses=[self.new_path]),
            dict(self.after, analyses=[other, self.new_path, self.old_path]),
        ):
            with self.subTest(after=after), self.assertRaises(AssertionError):
                candidate_changes("먹어도된다", before, after, [])

    def test_unattributed_addition_and_changed_record_fields_fail(self):
        after = deepcopy(self.after)
        after["analyses"][0]["rules"] = ["identity"]
        with self.assertRaises(AssertionError):
            candidate_changes("먹어도된다", self.before, after, [])
        with self.assertRaises(AssertionError):
            candidate_changes(
                "먹어도된다", self.before, dict(self.after, normalized="changed"), []
            )


if __name__ == "__main__":
    unittest.main()
