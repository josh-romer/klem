"""Reject altered annotations, recoveries, summaries, and individual contexts."""
import unittest
from unittest.mock import patch

import explanatory_se_corpora_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, obj, updates, reason):
        with patch.dict(obj, updates):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(*self.evidence)

    def alter_rows(self, mutation, reason):
        run = self.evidence[0]['runs'][0]
        rows = [audit.json.loads(line) for line in run['jsonl'].splitlines()]
        mutation(rows)
        text = ''.join(audit.json.dumps(row, ensure_ascii=False) + '\n' for row in rows)
        self.reject(run, {'jsonl': text, 'stdout_sha256': audit.sha(text.encode())}, reason)

    def test_complete_original_gold(self):
        result = audit.inspect(*self.evidence)
        self.assertEqual(result['original_gold_rows'], 66570)
        self.assertEqual(result['new_grouped_matches'], 2)
        self.assertEqual(result['new_recovered_lemmas'], 3)

    def test_missing_partition(self):
        self.reject(self.evidence[0], {'runs': self.evidence[0]['runs'][:-1]}, 'complete gold partitions')

    def test_missing_row_after_rehash(self):
        self.alter_rows(lambda rows: rows.pop(), 'complete original gold rows')

    def test_rewritten_lemma_target(self):
        self.alter_rows(lambda rows: rows[1].update(expected=['fabricated']), 'unaltered original gold identity')

    def test_false_recovery_after_rehash(self):
        self.alter_rows(lambda rows: rows[1].update(recovered=999), 'independently derived gold recovery')

    def test_false_candidate_mean_after_rehash(self):
        self.alter_rows(lambda rows: rows[0].update(mean_candidates=0), 'independently derived candidate')

    def test_false_transformed_recall_after_rehash(self):
        self.alter_rows(lambda rows: rows[0].update(transformed_grouped_recall=0), 'independently derived candidate')

    def test_incomplete_summary_deltas(self):
        run = next(run for run in self.evidence[0]['runs'] if run['summary_changes'])
        self.reject(run, {'summary_changes': {}}, 'complete summary delta accounting')

    def test_original_source_bound(self):
        self.reject(self.evidence[2]['corpora'][0], {'original_source_text': 'invented'}, 'original source bytes')

    def test_actual_adapter_bound(self):
        run = self.evidence[0]['runs'][0]
        self.reject(run, {'command': run['command'] + ['--fabricated']}, 'actual adapter command')

    def test_missing_individual_recovery(self):
        self.reject(self.evidence[0], {'individual_changed_rows': self.evidence[0]['individual_changed_rows'][:-1]}, 'complete changed row accounting')

    def test_invented_original_context(self):
        self.reject(self.evidence[4][0], {'complete_original_annotation_block': 'invented'}, 'complete original annotation block')

    def test_coordinated_rewritten_target(self):
        context = self.evidence[4][0]
        row = {**context['original_converted_row'], 'expected': ['invented']}
        self.reject(context, {'expected': ['invented'], 'original_converted_row': row}, 'independent original lemma targets')


if __name__ == '__main__':
    unittest.main()
