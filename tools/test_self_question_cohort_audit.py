"""Reject loss of candidates, original contexts, or dictionary assessments."""
import copy
import unittest
from unittest.mock import patch

import self_question_cohort_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def test_actual_full_cohorts_pass(self):
        self.assertEqual(audit.inspect(*self.evidence)["individual_unjudged_paths"], 14)

    def test_original_corpus_occurrence_loss(self):
        occurrence = self.evidence[0]["individual_additions"][0]
        with patch.dict(occurrence, original_occurrences=[]):
            with self.assertRaisesRegex(AssertionError, "original witnesses"):
                audit.inspect(*self.evidence)

    def test_history_fixture_pointer_changed(self):
        original = self.evidence[0]["individual_additions"][-1]
        witnesses = copy.deepcopy(original["original_occurrences"])
        witnesses[0]["pointer"] = "/invented"
        with patch.dict(original, original_occurrences=witnesses):
            with self.assertRaisesRegex(AssertionError, "history origins"):
                audit.inspect(*self.evidence)

    def test_dictionary_assessment_reclassified(self):
        original = self.evidence[0]["individual_additions"][0]
        changed = copy.deepcopy(original["dictionary_assessment"])
        changed["status"] = "compatible"
        with patch.dict(original, dictionary_assessment=changed):
            with self.assertRaisesRegex(AssertionError, "owner evidence"):
                audit.inspect(*self.evidence)

    def test_prior_candidate_removed_from_rehashed_capture(self):
        capture = self.evidence[0]["runs"][0]["captures"][1]
        surface = next(iter(capture["words"]))
        changed = copy.deepcopy(capture["words"][surface])
        changed["analyses"].pop(0)
        with patch.dict(capture["words"], {surface: changed}):
            with patch.dict(capture, word_sha256=audit.digest(capture["words"])):
                with self.assertRaisesRegex(AssertionError, "old candidate preservation"):
                    audit.inspect(*self.evidence)


if __name__ == "__main__":
    unittest.main()
