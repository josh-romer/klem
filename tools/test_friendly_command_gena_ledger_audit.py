"""Reject rewritten parent judgments or overbroad Gena promotion proposals."""
import copy
import json
import os
import unittest

import friendly_command_gena_ledger_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values=audit.inputs(draft=os.environ.get('KLEM_GENA_PROMOTION_DRAFT')=='1')

    def reject(self,field,change,reason):
        values=self.values.copy();values[field]=copy.deepcopy(values[field]);change(values)
        with self.assertRaisesRegex(AssertionError,reason):audit.inspect(values)

    def ledger(self,change,reason):
        def mutate(v):
            value=json.loads(v['current_raw']);change(value)
            v['current_raw']=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
        self.reject('current_raw',mutate,reason)

    def test_exact_original_draft(self):
        result=audit.inspect(self.values)
        self.assertEqual((result['current_cases'],result['current_reviews'],result['required'],result['forbidden']),(35764,520,31469,4312))
        self.assertFalse(result['historical_and_broad_hypotheses_promoted'])
        self.assertFalse(result['full_coverage_complete'])

    def test_parent_ledger_rewritten(self):
        self.reject('parent_raw',lambda v:v.update(parent_raw=b'{}'),'exact original35740 parent ledger bytes')

    def test_parent_reviews_rewritten(self):
        self.reject('parent_reviews_raw',lambda v:v.update(parent_reviews_raw=b'{}'),'exact original519 manual review bytes')

    def test_parent_queue_rewritten(self):
        self.reject('parent_queue_raw',lambda v:v.update(parent_queue_raw=b'{}'),'exact original715 source queue bytes')

    def test_original_proposal_rewritten(self):
        self.reject('proposed_raw',lambda v:v.update(proposed_raw=b'{}'),'exact unchanged24-case Gena proposal')

    def test_original_bounded_review_rewritten(self):
        self.reject('scoped_raw',lambda v:v.update(scoped_raw=b'{}'),'exact single bounded Gena review')

    def test_review_authoring_misreported(self):
        def change(v):
            d=json.loads(v['draft_raw']);d['review_draft_authored_after_runtime']=False;v['draft_raw']=json.dumps(d).encode()
        self.reject('draft_raw',change,'original honest Gena draft metadata')

    def test_independent_private_judgments_rewritten(self):
        self.reject('original_suite_raw',lambda v:v.update(original_suite_raw=b'{}'),'original preauthored Gena judgments')

    def test_case_missing(self):
        self.ledger(lambda d:d['cases'].pop(),'complete35740 parent plus24 cases')

    def test_original_case_lemma_changed(self):
        self.ledger(lambda d:d['cases'][0]['judgments'][0].update(lemmas=['invented']),'every old case field and relative order')

    def test_original_case_order_changed(self):
        self.ledger(lambda d:d['cases'].__setitem__(slice(0,2),d['cases'][:2][::-1]),'every old case field and relative order')

    def test_original_long_case_changed(self):
        self.ledger(lambda d:d['cases'][35704]['judgments'][0].update(verdict='forbidden'),'every old case field and relative order')

    def test_original_source_declaration_changed(self):
        self.ledger(lambda d:d['sources'].__setitem__(next(iter(d['sources'])),'https://example.invalid'),'only exact attributed source declarations')

    def test_original_case_serialized_bytes_changed(self):
        def change(v):v['current_raw']=v['current_raw'].replace(b'"cases": [\n    {',b'"cases": [\n     {',1)
        self.reject('current_raw',change,'every old serialized case byte')

    def test_gena_source_target_changed(self):
        self.ledger(lambda d:d['cases'][35740]['judgments'][0].update(lemmas=['invented']),'only exact24 preauthored cases appended')

    def test_forbidden_gena_case_promoted_to_required(self):
        self.ledger(lambda d:next(c for c in d['cases'][35740:] if c['judgments'][0]['verdict']=='forbidden')['judgments'][0].update(verdict='required'),'only exact24 preauthored cases appended')

    def test_actual_derived_dapda_shape_changed(self):
        self.ledger(lambda d:next(c for c in d['cases'][35740:] if c['surface']=='학생답게나')['judgments'][0].update(lemmas=['학생답다'],lemma_kinds=['predicate']),'only exact24 preauthored cases appended')

    def test_unjudged_history_word_substituted(self):
        self.ledger(lambda d:d['cases'][35740].update(surface='알려주시게나'),'only exact24 preauthored cases appended')

    def test_new_source_case_order_changed(self):
        self.ledger(lambda d:d['cases'].__setitem__(slice(35740,35742),d['cases'][35740:35742][::-1]),'only exact24 preauthored cases appended')

    def test_ledger_metadata_changed(self):
        self.ledger(lambda d:d.update(review_status='fully reviewed'),'original ledger metadata unchanged')

    def test_original_manual_review_changed(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][0].update(remaining='done'),'every old manual review field and relative order')

    def test_original_manual_review_order_changed(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'].__setitem__(slice(0,2),v['current_reviews']['entries'][:2][::-1]),'every old manual review field and relative order')

    def test_unjudged_broad_context_added_to_review(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][519]['judgments'].append(dict(case='unjudged-broad-보게나',judgment='required')),'only exact bounded Gena review appended')

    def test_own_remaining_review_scope_erased(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][519].update(remaining=''),'only exact bounded Gena review appended')


if __name__=='__main__':unittest.main()
