"""Reject lost histories, rewritten judgments and altered manual inventory reviews."""
import copy
import json
import unittest

import expression_conjectural_ledger_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.v)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(values)

    def current(self, values, mutate):
        ledger = json.loads(values['current_raw'])
        mutate(ledger)
        values['current_raw'] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()

    def test_complete_exact_histories(self):
        result = audit.inspect(self.v)
        self.assertEqual((result['active_cases'], result['required'], result['active_manual_reviews']), (35651, 31393, 513))
        self.assertFalse(result['full_coverage_complete'])

    def test_historical_expression_cannot_be_reauthored(self):
        self.reject(lambda v: v.update(expression_raw=b'{}'), 'exact expression historical ledger bytes')

    def test_historical_conjectural_cannot_be_reauthored(self):
        self.reject(lambda v: v.update(conjectural_raw=b'{}'), 'exact conjectural historical ledger bytes')

    def test_historical_manual_reviews_cannot_be_reauthored(self):
        self.reject(lambda v: v.update(parent_reviews_raw=b'{}'), 'exact historical manual review bytes')

    def test_current_cannot_drop_novel_case(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'].pop()), 'complete historical and active ledger sizes')

    def test_original_parent_reason_cannot_change(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][0]['judgments'][0].update(reason='invented')), 'every original expression parent case retained')

    def test_expression_case_cannot_change(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][35587]['judgments'][0].update(lemmas=['invented'])), 'every original expression parent case retained')

    def test_conjectural_copula_role_cannot_change(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][35630]['judgments'][0].update(lemma_kinds=['predicate'])), 'every original conjectural append retained')

    def test_second_novel_alternative_cannot_disappear(self):
        self.reject(lambda v: self.current(v, lambda d: next(c for c in d['cases'][35636:] if len(c['judgments']) == 2)['judgments'].pop()), 'every original conjectural append retained')

    def test_current_cannot_reformat_original_prefix(self):
        self.reject(lambda v: v.update(current_raw=(json.dumps(json.loads(v['current_raw']), ensure_ascii=False) + '\n').encode()), 'every original serialized expression prefix byte')

    def test_source_link_cannot_disappear(self):
        self.reject(lambda v: self.current(v, lambda d: d['sources'].pop(next(iter(d['sources'])))), 'every original branch source citation retained')

    def test_parent_review_evidence_cannot_disappear(self):
        self.reject(lambda v: v['current_reviews']['entries'][0].update(evidence=[]), 'every original manual review field retained')

    def test_parent_review_scope_cannot_expand(self):
        self.reject(lambda v: v['current_reviews']['entries'][0].update(scope='all Korean'), 'every original manual review field retained')

    def test_active_review_cannot_disappear(self):
        self.reject(lambda v: v['current_reviews']['entries'].pop(), 'complete original and active inventory review sizes')

    def test_extra_disposition_cannot_claim_an_unreviewed_owner(self):
        self.reject(lambda v: next(r for r in v['current_reviews']['entries'] if r['id'] == 'krdict:86084').update(id='krdict:invented'), 'only two bounded ending dispositions appended')

    def test_independent_judgment_cannot_be_refreshed(self):
        self.reject(lambda v: v['conjectural_cases'][0]['judgments'][0].update(lemmas=['invented']), 'fifty-six exact original conjectural judgments')


if __name__ == '__main__':
    unittest.main()
