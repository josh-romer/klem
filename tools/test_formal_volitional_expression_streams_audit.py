"""Reject incomplete expression streams and independently rederive required paths."""
import copy
import unittest

import formal_volitional_expression_streams_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, mutate, reason):
        packet, suite, report = copy.deepcopy(self.evidence)
        mutate(report)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(packet, suite, report)

    def test_all_complete_streams(self):
        self.assertEqual(audit.inspect(*self.evidence)['target_checks'], 192)

    def test_missing_unicode_cache_mode(self):
        self.reject(lambda r: r['runs'].pop(), 'all complete Unicode filter cache streams')

    def test_original_context_bytes(self):
        self.reject(lambda r: r['runs'][0].update(input_sha256='0' * 64), 'complete original input')

    def test_actual_filter_flag(self):
        self.reject(lambda r: r['runs'][2]['command'].remove('--dict-only'), 'actual filter cache command')

    def test_duplicate_surface_keeps_both_contexts(self):
        self.reject(lambda r: r['runs'][0]['matched_independent_targets'].pop(3), 'all independently rederived target occurrences')

    def test_candidate_cannot_be_promoted_by_match_metadata(self):
        def mutate(report):
            run = report['runs'][0]
            rows = [audit.json.loads(line) for line in run['jsonl'].splitlines()]
            index = run['matched_independent_targets'][4]['record_index']
            for path in rows[index]['analysis']['analyses']:
                if [lemma['text'] for lemma in path['lemmas']] == ['모으다']:
                    path['lemmas'][0]['text'] = '모다'
            run['jsonl'] = '\n'.join(audit.json.dumps(row, ensure_ascii=False) for row in rows) + '\n'
            run['jsonl_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject(mutate, 'every independently authored expression path')


if __name__ == '__main__':
    unittest.main()
