"""Reject lost or rewritten historical judgments in the prepared Sena append."""
import copy
import json
import unittest

import friendly_hortative_sena_ledger_draft_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = audit.inputs()

    def setUp(self):
        self.v = copy.deepcopy(self.original)

    def ledger(self):
        return json.loads(self.v['current_raw'])

    def reject_ledger(self, value, message):
        self.v['current_raw'] = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
        with self.assertRaisesRegex(AssertionError, message):
            audit.inspect(self.v)

    def test_complete_draft(self):
        self.assertEqual(audit.inspect(self.v)['proposed_cases'], 35789)

    def test_missing_required_case(self):
        value = self.ledger()
        del value['cases'][35764]
        self.reject_ledger(value, 'whole35764')

    def test_missing_forbidden_case(self):
        value = self.ledger()
        index = next(i for i in range(35764, len(value['cases'])) if value['cases'][i]['judgments'][0]['verdict'] == 'forbidden')
        del value['cases'][index]
        self.reject_ledger(value, 'whole35764')

    def test_extra_unjudged_tail(self):
        value = self.ledger()
        value['cases'].append(dict(id='unreviewed-extra', surface='가세나', judgments=[]))
        self.reject_ledger(value, 'whole35764')

    def test_changed_old_gena_case(self):
        value = self.ledger()
        value['cases'][35740]['judgments'][0]['verdict'] = 'forbidden'
        self.reject_ledger(value, 'all old judgments')

    def test_changed_sena_boundary(self):
        value = self.ledger()
        case = next(c for c in value['cases'][35764:] if c['judgments'][0]['verdict'] == 'forbidden')
        case['judgments'][0]['verdict'] = 'required'
        self.reject_ledger(value, 'only exact25')

    def test_runtime_rule_added_to_original_target(self):
        value = self.ledger()
        value['cases'][35764]['judgments'][0]['required_rules'] = ['ending.friendly_hortative.sena']
        self.reject_ledger(value, 'only exact25')

    def test_changed_old_source(self):
        value = self.ledger()
        old_key = next(iter(json.loads(self.v['parent_raw'])['sources']))
        value['sources'][old_key] = 'https://example.invalid/borrowed'
        self.reject_ledger(value, 'only exact Sena source')

    def test_changed_old_case_serialization(self):
        self.v['current_raw'] = self.v['current_raw'].replace(b'"cases": [\n    {', b'"cases": [\n     {', 1)
        with self.assertRaisesRegex(AssertionError, 'serialized case bytes'):
            audit.inspect(self.v)

    def test_changed_prior_review(self):
        self.v['current_reviews']['entries'][0]['scope'] = 'rewritten'
        with self.assertRaisesRegex(AssertionError, 'all old review fields'):
            audit.inspect(self.v)

    def test_missing_dialogue_source_judgment(self):
        self.v['current_reviews']['entries'][-1]['judgments'].pop()
        with self.assertRaisesRegex(AssertionError, 'only exact bounded Sena review'):
            audit.inspect(self.v)

    def test_corpus_hypothesis_promoted(self):
        self.v['metadata']['original_unjudged_corpus_hypothesis_promoted'] = True
        with self.assertRaises(AssertionError):
            audit.inspect(self.v)


if __name__ == '__main__':
    unittest.main()
