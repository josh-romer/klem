"""Reject rewritten parents, expanded scopes and unjudged candidate promotions."""
import copy
import json
import unittest

import gentle_command_ledger_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self, field, change, reason):
        value = self.values.copy();value[field] = copy.deepcopy(value[field])
        change(value)
        with self.assertRaisesRegex(AssertionError,reason):audit.inspect(value)

    def ledger(self, change, reason):
        def mutate(value):
            data = json.loads(value['current_raw']);change(data)
            value['current_raw'] = (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
        self.reject('current_raw',mutate,reason)

    def test_complete_exact_proposal(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['active_cases'],result['active_reviews']),(35704,517))
        self.assertFalse(result['full_coverage_complete'])
        self.assertFalse(result['unjudged_novel_or_history_paths_promoted'])

    def test_entire_current_scope_remains_mandatory(self):
        result = audit.inspect(self.values)
        current = json.loads(self.values['actual_current_raw'])
        self.assertEqual(result['complete_current_cases'],len(current['cases']))
        self.assertEqual(result['complete_current_reviews'],len(self.values['actual_current_reviews']['entries']))

    def test_parent_archive_cannot_be_refreshed(self):
        self.reject('parent_raw',lambda v:v.update(parent_raw=b'{}'),'exact original35681-case parent bytes')

    def test_original_review_archive_cannot_be_refreshed(self):
        self.reject('parent_reviews_raw',lambda v:v.update(parent_reviews_raw=b'{}'),'exact original515-review parent bytes')

    def test_scoped_dispositions_cannot_be_refreshed(self):
        self.reject('scoped_raw',lambda v:v.update(scoped_raw=b'{}'),'exact two independently recorded scoped dispositions')

    def test_parent_case_cannot_be_relabelled(self):
        self.ledger(lambda d:d['cases'][0]['judgments'][0].update(verdict='invented'),'every original parent case')

    def test_old_parent_cases_cannot_be_reordered(self):
        def change(d):d['cases'][0],d['cases'][1] = d['cases'][1],d['cases'][0]
        self.ledger(change,'every original parent case')

    def test_appended_case_cannot_be_removed(self):
        self.ledger(lambda d:d['cases'].pop(),'complete parent and23-case append')

    def test_appended_cases_cannot_be_reordered(self):
        def change(d):d['cases'][-1],d['cases'][-2] = d['cases'][-2],d['cases'][-1]
        self.ledger(change,'exact reviewed15required8forbidden append')

    def test_forbidden_boundary_cannot_be_required(self):
        self.ledger(lambda d:d['cases'][35695]['judgments'][0].update(verdict='required'),'exact reviewed15required8forbidden append')

    def test_source_lemma_cannot_change(self):
        self.ledger(lambda d:d['cases'][35681]['judgments'][0].update(lemmas=['invented']),'exact reviewed15required8forbidden append')

    def test_auxiliary_role_cannot_change(self):
        self.ledger(lambda d:d['cases'][-1]['judgments'][0].update(lemma_kinds=['predicate','predicate']),'exact reviewed15required8forbidden append')

    def test_required_ending_marker_cannot_disappear(self):
        self.ledger(lambda d:d['cases'][35681]['judgments'][0].update(required_rules=[]),'exact reviewed15required8forbidden append')

    def test_unjudged_novel_candidate_cannot_be_appended(self):
        self.ledger(lambda d:d['cases'].append({'id':'novel-unjudged','surface':'주렴','judgments':[]}),'complete parent and23-case append')

    def test_unjudged_novel_candidate_cannot_replace_source(self):
        self.ledger(lambda d:d['cases'][35681].update(surface='주렴'),'exact reviewed15required8forbidden append')

    def test_original_source_url_cannot_change(self):
        self.ledger(lambda d:d['sources'].update({next(iter(d['sources'])):'https://example.invalid/changed'}),'all original and only independently reviewed source citations')

    def test_new_source_url_cannot_change(self):
        self.ledger(lambda d:d['sources'].update({'gentle-command-79340':'https://example.invalid/changed'}),'all original and only independently reviewed source citations')

    def test_unreviewed_source_alias_cannot_be_added(self):
        self.ledger(lambda d:d['sources'].update(invented='https://example.invalid/'),'all original and only independently reviewed source citations')

    def test_parent_coverage_claim_cannot_expand(self):
        self.ledger(lambda d:d.update(review_status='complete Korean coverage'),'original parent ledger metadata')

    def test_old_manual_review_cannot_change(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][0].update(scope='invented'),'every original manual review field/order')

    def test_old_review_metadata_cannot_claim_independent_review(self):
        self.reject('current_reviews',lambda v:v['current_reviews'].update(review_status='independent review complete'),'original manual review metadata')

    def test_new_ending_review_cannot_disappear(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'].pop(),'exact parent and two scoped reviews')

    def test_new_review_cannot_claim_full_coverage(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][-1].update(status='complete'),'only exact bounded gentle reviews appended')

    def test_new_review_cannot_drop_limitations(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][-1].update(remaining=''),'only exact bounded gentle reviews appended')

    def test_new_review_cannot_borrow_willingness_owner(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][-1].update(id='krdict:76567'),'only exact bounded gentle reviews appended')

    def test_new_review_cannot_omit_original_group(self):
        self.reject('current_reviews',lambda v:v['current_reviews']['entries'][-1]['judgments'].pop(),'only exact bounded gentle reviews appended')


if __name__ == '__main__':
    unittest.main()
