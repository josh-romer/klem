"""Controls for complete corpus/history preservation replay evidence."""

import copy
import unittest
from unittest.mock import patch

import explanatory_se_cohort_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def test_complete_cohorts(self):
        report = audit.inspect(*self.evidence)
        self.assertEqual(report["corpus_surfaces"] + report["historical_surfaces"], 53502)
        self.assertEqual(report["individual_unjudged_paths"], 15)

    def test_missing_surface_after_rehash(self):
        capture = self.evidence[0]["runs"][0]["captures"][1]
        words = dict(capture["words"])
        words.pop(next(iter(words)))
        with patch.dict(capture, words=words, word_sha256=audit.digest(words)):
            with self.assertRaisesRegex(AssertionError, "complete cohort surfaces"):
                audit.inspect(*self.evidence)

    def test_removed_prior_candidate_after_rehash(self):
        capture = self.evidence[0]["runs"][0]["captures"][1]
        surface = next(iter(capture["words"]))
        changed = copy.deepcopy(capture["words"][surface])
        changed["analyses"].pop(0)
        with patch.dict(capture["words"], {surface: changed}):
            with patch.dict(capture, word_sha256=audit.digest(capture["words"])):
                with self.assertRaisesRegex(AssertionError, "old candidate preservation"):
                    audit.inspect(*self.evidence)

    def test_changed_historical_baseline(self):
        capture = self.evidence[0]["runs"][1]["captures"][0]
        words = dict(capture["words"])
        words.pop(next(iter(words)))
        with patch.dict(capture, words=words, word_sha256=audit.digest(words)):
            with self.assertRaisesRegex(AssertionError, "complete historical baseline"):
                audit.inspect(*self.evidence)

    def test_invented_addition(self):
        report = self.evidence[0]
        with patch.dict(report, individual_additions=report["individual_additions"] + [{"id": "invented"}]):
            with self.assertRaisesRegex(AssertionError, "complete individual additions"):
                audit.inspect(*self.evidence)


    def reject_item(self,obj,updates,reason):
        with patch.dict(obj,updates):
            with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*self.evidence)

    def test_complete_individual_context(self):
        item=self.evidence[0]["individual_additions"][0]
        self.reject_item(item,{"original_occurrences":item["original_occurrences"][:-1]},"complete original witnesses")

    def test_context_not_promoted_to_gold(self):
        self.reject_item(self.evidence[0]["individual_additions"][0],{"contextual_verdict":"required"},"individual original path and owner evidence")

    def test_complete_native_fields(self):
        ident=next(iter(self.evidence[0]["complete_native_entries"]))
        self.reject_item(self.evidence[0]["complete_native_entries"][ident],{"headword":"fabricated"},"complete original Native fields")

    def test_original_distribution_projection(self):
        ident=next(iter(self.evidence[4]))
        self.reject_item(self.evidence[4][ident],{"pos":"fabricated"},"complete distribution Native projection")

    def test_original_distribution_unknown_fields(self):
        lexical=self.evidence[5]["LexicalResource"]["Lexicon"]["LexicalEntry"][0]
        self.reject_item(lexical,{"invented":"coordinated"},"pinned complete original distribution Native fields")

    def test_stable_individual_id(self):
        self.reject_item(self.evidence[0]["individual_additions"][0],{"id":"invented"},"individual addition identity")

    def test_original_gold_occurrence_not_rewritten(self):
        row=self.evidence[0]["individual_additions"][0]["original_occurrences"][0]["original_gold_row"]
        self.reject_item(row,{"expected":["invented"]},"complete original corpus occurrences")


if __name__ == "__main__":
    unittest.main()
