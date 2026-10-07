"""Reject fabricated corpus recovery/ambiguity and incomplete exact-parent proof."""
import copy
import json
import unittest

from reported_deoni_corpora import read, verify_rows
from reported_deoni_parent import actual_parent


class ReportedCorpusEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = read('docs/reported-deoni-prototype-corpora.json.gz')
        cls.corpus_run = next(run for run in cls.capture['corpora'] if run['changed_gold_outcomes'])
        cls.rows = [json.loads(line) for line in cls.corpus_run['after_jsonl'].splitlines()]

    def test_actual_corpus_outcomes_and_candidate_summaries_agree(self):
        result = verify_rows(self.rows, self.capture['after_words'])
        self.assertEqual(result['rows'], 9871)
        self.assertTrue(result['gold_outcomes_verified'])

    def test_changed_original_gold_lemma_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        case = next(row for row in rows[1:] if row['id'] == 'id:test-s619/2')
        case['expected'] = ['invented-gold']
        with self.assertRaises(AssertionError):
            verify_rows(rows, self.capture['after_words'])

    def test_fabricated_recovery_indices_are_rejected(self):
        rows = copy.deepcopy(self.rows)
        case = next(row for row in rows[1:] if row['id'] == 'id:test-s619/2')
        case['recovered_sets'] = [[0, 1]]
        case['recovered'] = 2
        with self.assertRaises(AssertionError):
            verify_rows(rows, self.capture['after_words'])

    def test_changed_ambiguity_summary_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['mean_candidates'] += .1
        with self.assertRaises(AssertionError):
            verify_rows(rows, self.capture['after_words'])

    def test_missing_or_wrong_old_companion_is_rejected(self):
        observation = self.capture['candidate_changes'][0]
        parents = self.capture['actual_prior_companions']
        self.assertEqual(actual_parent(observation['surface'], observation['analysis'], parents),
                         (observation['parent_surface'], observation['exact_parent']))
        with self.assertRaises(AssertionError):
            actual_parent(observation['surface'], observation['analysis'], {})
        incorrect = copy.deepcopy(parents)
        incorrect[observation['parent_surface']]['analyses'] = []
        with self.assertRaises(AssertionError):
            actual_parent(observation['surface'], observation['analysis'], incorrect)


if __name__ == '__main__':
    unittest.main()
