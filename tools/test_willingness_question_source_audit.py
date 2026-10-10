"""Reject altered original owners, judgments, contexts and baseline claims."""
import copy
import unittest

import willingness_question_source_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.values)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(values)

    def test_original_source_evidence(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['source_cases'], result['boundary_cases'], result['native_owners']), (10, 12, 29))
        self.assertFalse(result['full_coverage_complete'])

    def test_original_source_bytes(self):
        self.reject(lambda v: v.update(source_raw=b'{}'), 'original authored source bytes')

    def test_ending_context_cannot_be_cropped(self):
        self.reject(lambda v: v['source']['items'][0]['complete_original_group'].pop(), 'original authored source fields')

    def test_expression_cannot_borrow_an_ending_role(self):
        self.reject(lambda v: v['source']['separate_expression_groups'][0].update(morphological_judgment='required ending'), 'original authored source fields')

    def test_source_target_cannot_be_refreshed(self):
        self.reject(lambda v: v['gold']['cases'][0]['judgments'][0].update(lemmas=['invented']), 'every independent source judgment unchanged')

    def test_boundary_cannot_reject_all_hypotheses(self):
        self.reject(lambda v: v['boundary_gold']['cases'][-1]['judgments'][0].update(morphemes=[]), 'exact boundary path only')

    def test_boundary_verdict_cannot_change(self):
        self.reject(lambda v: v['boundary_gold']['cases'][-1]['judgments'][0].update(verdict='required'), 'original boundary verdict and reason')

    def test_native_translation_cannot_disappear(self):
        self.reject(lambda v: v['entries']['krdict:76564']['senses'][0]['translations'].pop(), 'every complete original Native field')

    def test_native_regular_homonym_cannot_disappear(self):
        self.reject(lambda v: v['entries'].pop('krdict:25357'), 'all twenty-nine original Native owners')

    def test_expression_label_owner_is_not_an_ending(self):
        self.reject(lambda v: v['label']['sources'][0].update(id=86640, pos='품사 없음'), 'label does not borrow expression ownership')

    def test_baseline_cannot_drop_unicode_cache_stream(self):
        self.reject(lambda v: v['baseline']['runs'].pop(), 'complete prior installed baseline')

    def test_complete_prior_output_cannot_change(self):
        self.reject(lambda v: v['baseline']['runs'][0].update(jsonl='{}\n'), 'complete prior ordered output bytes')

    def test_existing_lemma_cannot_be_reported_missing(self):
        self.reject(lambda v: v['baseline']['runs'][0]['observations'][0].update(lexical_path_indices=[]), 'prior lexical alternatives already present')

    def test_missing_ending_cannot_be_reported_present(self):
        self.reject(lambda v: v['baseline']['runs'][0]['observations'][0].update(typed_ending_path_indices=[0]), 'baseline decomposition gap is separate from lexical recall')


if __name__ == '__main__':
    unittest.main()
