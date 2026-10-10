import copy
import unittest
import reported_experience_performance as audit


class PerformanceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def corrupt(self, change, reason):
        values = copy.deepcopy(self.values)
        change(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_actual_complete_pair_passes(self):
        self.assertEqual(audit.inspect(*self.values)['samples'], 80)

    def test_nonterminal_capture_rejected(self):
        self.corrupt(lambda v:v[0].update(state='running'), 'complete terminal')

    def test_later_release_substitution_rejected(self):
        self.corrupt(lambda v:v[4]['packages'][1].update(head='later-version'), 'original release revisions')

    def test_sample_missing_rejected(self):
        self.corrupt(lambda v:v[0]['workloads'][0]['samples'].pop(), 'all ten interleaved')

    def test_omitted_workload_rejected(self):
        self.corrupt(lambda v:v[0]['workloads'].pop(), 'all eight complete')

    def test_removed_spacing_flag_rejected(self):
        self.corrupt(lambda v:v[0]['workloads'][-1]['samples'][0]['command'].remove('--suggest-spacing'), 'actual full workload command')

    def test_summary_rewrite_rejected(self):
        self.corrupt(lambda v:v[0]['workloads'][0]['summary']['after'].update(median_seconds=0), 'independently recomputed summaries')

    def test_partial_cache_output_rejected(self):
        self.corrupt(lambda v:v[0]['cache_parity'][0]['checks'][0].update(records=179111), 'full cache-parity output binding')

    def test_cache_budget_rewrite_rejected(self):
        self.corrupt(lambda v:v[0]['cache_parity'][0]['checks'][0].update(cache_bytes=8388608), 'both complete cache budgets')

    def test_nonfinite_timing_rejected(self):
        self.corrupt(lambda v:v[0]['workloads'][0]['samples'][0].update(seconds=float('nan')), 'actual finite timing')


if __name__ == '__main__':
    unittest.main()
