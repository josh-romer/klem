"""Reject omitted tails even when a caller requests only a historical view."""
import copy
import json
import unittest

import friendly_hortative_sena_ledger_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = audit.inputs(draft=True)

    def setUp(self):
        self.v = copy.deepcopy(self.original)

    def reject_case(self, mutate, reason):
        ledger = json.loads(self.v['current_raw'])
        mutate(ledger)
        self.v['current_raw'] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()
        with self.assertRaisesRegex(AssertionError, reason):
            audit.historical_parent(self.v)

    def test_complete_original_append(self):
        result = audit.inspect(self.v)
        self.assertEqual((result['current_cases'], result['current_reviews']), (35789, 521))
        self.assertEqual((result['original_required'], result['original_forbidden']), (19, 6))
        self.assertFalse(result['actual_shared_promotion'])
        self.assertFalse(result['full_coverage_complete'])

    def test_checked_historical_parent(self):
        parent = audit.historical_parent(self.v)
        self.assertEqual(parent['current_raw'], self.v['original']['parent_raw'])
        self.assertEqual(len(parent['current_reviews']['entries']), 520)

    def test_parent_cannot_hide_tail(self):
        self.v['current_raw'] = self.v['original']['parent_raw']
        with self.assertRaisesRegex(AssertionError, 'complete35764'):
            audit.historical_parent(self.v)

    def test_missing_required_tail(self):
        self.reject_case(lambda d: d['cases'].pop(35764), 'complete35764')

    def test_missing_forbidden_tail(self):
        def mutate(d):
            index = next(i for i in range(35764, 35789)
                         if d['cases'][i]['judgments'][0]['verdict'] == 'forbidden')
            d['cases'].pop(index)
        self.reject_case(mutate, 'complete35764')

    def test_unknown_unjudged_tail(self):
        self.reject_case(lambda d: d['cases'].append(dict(id='unknown', surface='중세나', judgments=[])), 'complete35764')

    def test_changed_parent_candidate(self):
        self.reject_case(lambda d: d['cases'][35740]['judgments'][0].update(lemmas=['invented']), 'all35764 parent')

    def test_changed_sena_candidate(self):
        self.reject_case(lambda d: d['cases'][35764]['judgments'][0].update(lemmas=['invented']), 'only exact25')

    def test_new_runtime_rule_requirement(self):
        self.reject_case(lambda d: d['cases'][35764]['judgments'][0].update(required_rules=['invented']), 'only exact25')

    def test_changed_serialized_parent(self):
        self.v['current_raw'] = self.v['current_raw'].replace(b'"cases": [\n    {', b'"cases": [\n     {', 1)
        with self.assertRaisesRegex(AssertionError, 'serialized parent'):
            audit.historical_parent(self.v)

    def test_reordered_parent(self):
        def mutate(d):
            d['cases'][0], d['cases'][1] = d['cases'][1], d['cases'][0]
        self.reject_case(mutate, 'all35764 parent')

    def test_changed_source_declaration(self):
        self.reject_case(lambda d: d['sources'].update({next(iter(d['sources'])): 'https://example.invalid'}), 'source declaration')

    def test_changed_ledger_metadata(self):
        self.reject_case(lambda d: d.update(unreviewed_is_correct=True), 'ledger metadata')

    def test_missing_review(self):
        self.v['current_reviews']['entries'].pop()
        with self.assertRaisesRegex(AssertionError, 'complete520'):
            audit.historical_parent(self.v)

    def test_changed_old_review(self):
        self.v['current_reviews']['entries'][0]['scope'] = 'all Korean'
        with self.assertRaisesRegex(AssertionError, 'all520'):
            audit.historical_parent(self.v)

    def test_unbounded_sena_review(self):
        self.v['current_reviews']['entries'][-1]['remaining'] = ''
        with self.assertRaisesRegex(AssertionError, 'exact bounded'):
            audit.historical_parent(self.v)

    def test_missing_original_dialogue_judgment(self):
        self.v['current_reviews']['entries'][-1]['judgments'].pop()
        with self.assertRaisesRegex(AssertionError, 'exact bounded'):
            audit.historical_parent(self.v)

    def test_changed_whole_native_group(self):
        self.v['original']['author_raw'] = self.v['original']['author_raw'].replace('하세나'.encode(), '합세나'.encode(), 1)
        with self.assertRaisesRegex(AssertionError, 'original preauthored suite'):
            audit.historical_parent(self.v)


if __name__ == '__main__':
    unittest.main()
