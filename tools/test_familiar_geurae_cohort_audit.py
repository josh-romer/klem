"""Controls for complete corpus/history preservation replay evidence."""

import copy
import unittest
from unittest.mock import patch

import familiar_geurae_cohort_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def test_complete_cohorts(self):
        report = audit.inspect(*self.evidence)
        self.assertEqual(report["corpus_surfaces"] + report["historical_surfaces"], 53502)
        self.assertEqual(report["individual_unjudged_paths"], 0)

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


if __name__ == "__main__":
    unittest.main()
