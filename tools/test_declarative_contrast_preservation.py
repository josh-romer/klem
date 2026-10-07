import copy
import unittest
import declarative_contrast_preservation as a


class BroadGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = a.read(a.ROOT / 'docs/declarative-contrast-prototype-broad.json.gz')
        cls.prior = a.read(a.ROOT/'docs/literary-ri-prefinal-prototype-broad.json.gz')
        cls.native = a.read(a.ROOT / 'docs/declarative-contrast-broad-owner-preparation.json.gz')['complete_native_entries']

    def reject(self, change):
        report = copy.deepcopy(self.report)
        change(report)
        with self.assertRaises((AssertionError, KeyError, ValueError)):
            a.verify_broad(report,self.prior,self.native)

    def test_all_captured_changes_are_individually_derived(self):
        self.assertEqual(a.verify_broad(self.report,self.prior,self.native)['individually_unjudged_additions'],55)

    def test_changed_helper_cannot_certify_old_capture_even_with_matching_self_hash(self):
        def change(d):
            d['inversion_helper']['text'] += '\n# altered helper\n'
            d['inversion_helper']['sha256'] = a.sha(d['inversion_helper']['text'].encode())
        self.reject(change)

    def test_observation_cannot_disappear(self):
        self.reject(lambda d:d['individual_additions'].pop())

    def test_duplicate_stream_cannot_replace_a_spacing_mode(self):
        self.reject(lambda d:d['comparisons'].__setitem__(-1,d['comparisons'][0]))

    def test_prior_stream_hash_cannot_drift(self):
        self.reject(lambda d:d['comparisons'][0].__setitem__('before_jsonl_sha256','0'*64))

    def test_source_span_cannot_move(self):
        self.reject(lambda d:d['comparisons'][0]['changed_frames'][0]['after']['span'].__setitem__('start',0))

    def test_candidate_cannot_borrow_another_old_particle_parent(self):
        self.reject(lambda d:d['individual_additions'][0]['exact_split_particle_parent']['lemmas'][0].__setitem__('text','unrelated'))

    def test_structural_precision_cannot_be_inferred_from_preservation(self):
        self.reject(lambda d:d['individual_additions'][0].__setitem__('structural_verdict','required'))

    def test_dictionary_assessment_cannot_disappear(self):
        self.reject(lambda d:d['comparisons'][0]['changed_frames'][0]['after']['dictionary']['readings'].pop())


class CorpusGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = a.read(a.ROOT / 'docs/declarative-contrast-prototype-corpora.json.gz')
        cls.adapter = a.read(a.ROOT / 'docs/declarative-contrast-prototype-adapter.json.gz')
        cls.prior = a.read(a.ROOT/'docs/literary-ri-prefinal-prototype-corpora.json.gz')

    def reject(self, change):
        report,adapter = copy.deepcopy(self.report),copy.deepcopy(self.adapter)
        change(report,adapter)
        with self.assertRaises((AssertionError,KeyError,ValueError)):
            a.verify_corpora(report,adapter,self.prior)

    def test_all_original_gold_rows_and_actual_adapter_outputs(self):
        self.assertEqual(a.verify_corpora(self.report,self.adapter,self.prior)['changed_gold_outcomes'],0)

    def test_added_candidate_cannot_disappear_from_tracking(self):
        self.reject(lambda d,adapter:d['candidate_changes'].pop())

    def test_original_gold_row_cannot_change(self):
        self.reject(lambda d,adapter:d['corpora'][0]['original_converted_rows'][0]['expected'].append('invented'))

    def test_source_context_cannot_disappear(self):
        self.reject(lambda d,adapter:d['candidate_changes'][0]['occurrences'].pop())

    def test_candidate_growth_cannot_be_hidden_in_summary(self):
        self.reject(lambda d,adapter:d['corpora'][0]['after_summary'].__setitem__('candidate_count_sum',0))

    def test_native_gold_outcome_cannot_be_forged(self):
        self.reject(lambda d,adapter:d['corpora'][0]['comparisons'][0]['after'].__setitem__('recovered',999))

    def test_actual_adapter_hash_cannot_change(self):
        self.reject(lambda d,adapter:adapter['runs'][0]['streams'][1].__setitem__('sha256','0'*64))


if __name__ == '__main__':
    unittest.main()
