"""Reject rewritten long-ending parents, private judgments and expanded reviews."""
import copy
import json
import os
import unittest

import gentle_command_long_ledger_audit as audit
import gentle_command_ledger_audit as historical


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs(draft=os.environ.get('KLEM_LONG_PROMOTION_DRAFT')=='1')

    def reject(self, field, change, reason):
        value = self.values.copy();value[field] = copy.deepcopy(value[field]);change(value)
        with self.assertRaisesRegex(AssertionError, reason): audit.inspect(value)

    def ledger(self, change, reason):
        def mutate(value):
            ledger = json.loads(value['current_raw']);change(ledger)
            value['current_raw']=(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n').encode()
        self.reject('current_raw',mutate,reason)

    def test_complete_exact_original_append(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['active_cases'],result['active_reviews'],result['required'],result['forbidden']), (35740,519,31452,4305))
        self.assertFalse(result['novel8preauthored'])
        self.assertFalse(result['other11rawnovel_promoted'])
        self.assertFalse(result['full_coverage_complete'])

    def test_original_parent_bytes(self):
        self.reject('parent_raw',lambda v:v.update(parent_raw=b'{}'),'exact original35704 parent ledger bytes')

    def test_original_parent_reviews(self):
        self.reject('parent_reviews_raw',lambda v:v.update(parent_reviews_raw=b'{}'),'exact original517 parent review bytes')

    def test_original_long_dispositions(self):
        self.reject('scoped_raw',lambda v:v.update(scoped_raw=b'{}'),'exact bounded long-ending review dispositions')

    def test_original_proposal(self):
        self.reject('proposed_raw',lambda v:v.update(proposed_raw=b'{}'),'exact original36-case long proposal')

    def test_honest_post_runtime_novel_scope(self):
        def mutate(v):
            d=json.loads(v['draft_raw']);d['novel8_authoring_precedes_runtime']=True
            v['draft_raw']=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
        self.reject('draft_raw',mutate,'unchanged original long draft metadata')

    def test_original_novel_fixture_cannot_be_refreshed(self):
        self.reject('suite_raw',lambda v:v['suite_raw'].__setitem__(1,b'{}'),'all three original private judgment fixtures')

    def test_case_cannot_disappear(self):
        self.ledger(lambda d:d['cases'].pop(),'complete original parent and36-case append')

    def test_original_parent_case_field(self):
        self.ledger(lambda d:d['cases'][0]['judgments'][0].update(reason='changed'),'every original parent case field and order')

    def test_original_parent_case_order(self):
        def mutate(d):d['cases'][0],d['cases'][1]=d['cases'][1],d['cases'][0]
        self.ledger(mutate,'every original parent case field and order')

    def test_original_short_gentle_case(self):
        self.ledger(lambda d:d['cases'][35681]['judgments'][0].update(lemmas=['invented']),'every original parent case field and order')

    def test_long_source_case_order(self):
        def mutate(d):d['cases'][35704],d['cases'][35705]=d['cases'][35705],d['cases'][35704]
        self.ledger(mutate,'only exact25preauthored8novel3derived judgments appended')

    def test_long_forbidden_verdict(self):
        self.ledger(lambda d:next(c for c in d['cases'][35704:] if c['judgments'][0]['verdict']=='forbidden')['judgments'][0].update(verdict='required'),'only exact25preauthored8novel3derived judgments appended')

    def test_known_derived_adjective_shape(self):
        self.ledger(lambda d:d['cases'][-3]['judgments'][0].update(lemmas=['학생답다'],lemma_kinds=['predicate']),'only exact25preauthored8novel3derived judgments appended')

    def test_novel_original_byte_identity(self):
        self.ledger(lambda d:d['cases'][35729].update(id='long-gentle-novel-0-15'),'only exact25preauthored8novel3derived judgments appended')

    def test_novel_source_lexical_head(self):
        self.ledger(lambda d:d['cases'][35729]['judgments'][0].update(lemmas=['invented']),'only exact25preauthored8novel3derived judgments appended')

    def test_unjudged_novel_hypothesis(self):
        self.ledger(lambda d:d['cases'].append({'id':'unjudged-novel','surface':'하려무나','judgments':[]}),'complete original parent and36-case append')

    def test_original_serialized_parent(self):
        self.reject('current_raw',lambda v:v.update(current_raw=json.dumps(json.loads(v['current_raw']),ensure_ascii=False).encode()),'every original serialized35704 case byte')

    def test_original_source_url(self):
        self.ledger(lambda d:d['sources'].update({next(iter(d['sources'])):'https://invalid.example'}),'all original and only exact reviewed source citations')

    def test_new_source_url(self):
        self.ledger(lambda d:d['sources'].update({'gentle-command-long-79266':'https://invalid.example'}),'all original and only exact reviewed source citations')

    def test_unreviewed_source_alias(self):
        self.ledger(lambda d:d['sources'].update(invented='https://invalid.example'),'all original and only exact reviewed source citations')

    def test_original_coverage_metadata(self):
        self.ledger(lambda d:d.update(review_status='all Korean'),'original ledger metadata remains bounded')

    def test_original_review_scope(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][0].update(scope='all Korean'),'every original manual review field and order')

    def test_original_short_review_scope(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][516].update(remaining='none'),'every original manual review field and order')

    def test_missing_long_review(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'].pop(),'complete original517 and two long reviews')

    def test_long_review_cannot_claim_completion(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][517].update(status='complete'),'only exact bounded long reviews appended')

    def test_long_review_original_source_hash(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][518].update(source_sha256='invented'),'only exact bounded long reviews appended')

    def test_long_review_cannot_borrow_short_owner(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][517].update(id='krdict:79340'),'only exact bounded long reviews appended')

    def integrated(self):
        values = historical.original_inputs();complete = self.values
        values.update(current_raw=complete['parent_raw'],current_reviews=json.loads(complete['parent_reviews_raw']),
                      actual_current_raw=complete['current_raw'],actual_current_reviews=complete['current_reviews'],long_append=complete)
        return values

    def test_historical_and_entire_current_scope(self):
        result = historical.inspect(self.integrated())
        self.assertEqual((result['active_cases'],result['active_reviews']),(35704,517))
        self.assertEqual((result['complete_current_cases'],result['complete_current_reviews']),(35740,519))

    def test_historical_projection_cannot_skip_long_check(self):
        values=self.integrated();del values['long_append']
        with self.assertRaises(KeyError):historical.inspect(values)

    def test_current_projection_cannot_hide_another_tail(self):
        values=self.integrated();values['actual_current_raw']=b'{}'
        with self.assertRaisesRegex(AssertionError,'mandatory complete current long ledger bytes'):historical.inspect(values)

    def test_current_projection_cannot_hide_review_change(self):
        values=self.integrated();values['actual_current_reviews']=copy.deepcopy(values['actual_current_reviews']);values['actual_current_reviews']['entries'][-1]['scope']='all Korean'
        with self.assertRaisesRegex(AssertionError,'mandatory complete current long review fields'):historical.inspect(values)


if __name__=='__main__':
    unittest.main()
