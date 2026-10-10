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
        self.assertEqual((result['active_cases'], result['required'], result['active_manual_reviews']), (35704, 31427, 517))
        self.assertEqual((result['historical']['active_cases'], result['historical']['required'],
                          result['historical']['active_manual_reviews']), (35681, 31412, 515))
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
        self.reject(lambda v: next(r for r in v['current_reviews']['entries'] if r['id'] == 'krdict:86084').update(id='krdict:invented'), 'only two conjectural and two willingness dispositions appended')

    def test_independent_judgment_cannot_be_refreshed(self):
        self.reject(lambda v: v['conjectural_cases'][0]['judgments'][0].update(lemmas=['invented']), 'fifty-six exact original conjectural judgments')

    def test_willingness_source_cannot_be_reauthored(self):
        self.reject(lambda v: v['willingness_raw'].__setitem__(0, b'{}'), 'exact independently authored willingness judgments')

    def test_willingness_append_cannot_change_verdict(self):
        self.reject(lambda v: self.current(v, lambda d: next(c for c in d['cases'] if c['id'] == 'willingness-question-stem-boundary-12')['judgments'][0].update(verdict='required')), 'every exact original willingness append retained')


    def test_pre_interaction_history_cannot_be_reauthored(self):
        self.reject(lambda v: v.update(interaction_parent_raw=b'{}'), 'exact pre-interaction ledger bytes')

    def test_interaction_fixture_cannot_be_reauthored(self):
        self.reject(lambda v: v.update(interaction_raw=b'{}'), 'exact independently authored interaction judgments')

    def test_interaction_lemma_role_cannot_change(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][35679]['judgments'][0].update(lemma_kinds=['predicate', 'predicate'])), 'every exact independently authored interaction append retained')

    def test_interaction_verdict_cannot_change(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][35675]['judgments'][0].update(verdict='required')), 'every exact independently authored interaction append retained')

    def test_pre_willingness_review_archive_cannot_be_refreshed(self):
        self.reject(lambda v: v.update(willingness_parent_reviews_raw=b'{}'), 'exact pre-willingness inventory review bytes')

    def test_original_conjectural_review_cannot_expand_its_scope(self):
        self.reject(lambda v: v['current_reviews']['entries'][512].update(scope='all Korean'), 'every pre-willingness manual review field and order retained')

    def test_willingness_review_cannot_expand_its_scope(self):
        self.reject(lambda v: v['current_reviews']['entries'][513].update(scope='all Korean'), 'only exact independently recorded willingness reviews appended')

    def test_willingness_review_source_hash_cannot_change(self):
        self.reject(lambda v: v['current_reviews']['entries'][514].update(source_sha256='invented'), 'only exact independently recorded willingness reviews appended')

    def test_coordinated_willingness_review_rewrite_is_rejected(self):
        def mutate(v):
            authored = json.loads(v['willingness_reviews_raw'])
            authored['entries'][0]['remaining'] = 'nothing'
            v['current_reviews']['entries'][513]['remaining'] = 'nothing'
            v['willingness_reviews_raw'] = (json.dumps(authored, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'exact bounded willingness dispositions')

    def test_review_cannot_borrow_expression_owner(self):
        self.reject(lambda v: v['willingness_source']['ending_owner_ids'].__setitem__(0, 'krdict:86640'), 'both original ending owners reviewed separately')

    def test_original_source_digest_cannot_change_with_review(self):
        self.reject(lambda v: v['willingness_source']['owners']['krdict:76567'].update(notes=['invented']), 'complete original inventory source digest for bounded review')


    def test_complete_current_append_cannot_be_dropped(self):
        def mutate(v):
            ledger = json.loads(v['gentle_append']['current_raw'])
            ledger['cases'].pop()
            v['gentle_append']['current_raw'] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'complete parent and23-case append')

    def test_complete_current_forbidden_judgment_cannot_change(self):
        def mutate(v):
            ledger = json.loads(v['gentle_append']['current_raw'])
            ledger['cases'][35695]['judgments'][0]['verdict'] = 'required'
            v['gentle_append']['current_raw'] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'exact reviewed15required8forbidden append')

    def test_complete_current_review_cannot_expand(self):
        self.reject(lambda v: v['gentle_append']['current_reviews']['entries'][-1].update(status='complete'),
                    'only exact bounded gentle reviews appended')

    def test_complete_current_cannot_append_an_unjudged_novel(self):
        def mutate(v):
            ledger = json.loads(v['gentle_append']['current_raw'])
            ledger['cases'].append({'id': 'unjudged-novel', 'surface': '주렴', 'judgments': []})
            v['gentle_append']['current_raw'] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'complete parent and23-case append')

    def test_historical_projection_cannot_omit_complete_current_check(self):
        values = copy.deepcopy(self.v)
        del values['gentle_append']
        with self.assertRaises(KeyError):
            audit.inspect(values)


if __name__ == '__main__':
    unittest.main()
