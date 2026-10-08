"""Guard paired workload validation using an existing real timing capture."""
import copy
import unittest
from functools import lru_cache
from unittest.mock import patch

from ostensible_reason_audit import ROOT, read
from literary_question_go_performance import verify_samples
import literary_question_go_performance as audit


class TimingGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workloads = read(ROOT/'docs/literary-question-go-performance.json')['workloads']
        cls.binaries = {version:next(r['command'][0] for w in cls.workloads
                                    for r in w['samples'] if r['version']==version)
                        for version in ['before','after']}
        cls.book = cls.workloads[0]['samples'][0]['command'][2]
        cls.dictionary = next(r['command'][6] for w in cls.workloads
                              for r in w['samples'] if '--dictionary' in r['command'])

    def reject(self, mutate):
        workloads = copy.deepcopy(self.workloads)
        mutate(workloads)
        with self.assertRaises((AssertionError, KeyError, ValueError)):
            verify_samples(workloads,self.binaries,self.book,self.dictionary)

    def test_all_actual_paired_samples_pass(self):
        self.assertEqual(verify_samples(self.workloads,self.binaries,self.book,self.dictionary),80)

    def test_sample_cannot_disappear(self):
        self.reject(lambda w:w[0]['samples'].pop())

    def test_alternating_order_cannot_be_replaced(self):
        self.reject(lambda w:w[0]['samples'].__setitem__(2,w[0]['samples'][0]))

    def test_cached_mode_cannot_replace_uncached_mode(self):
        self.reject(lambda w:w.__setitem__(0,w[1]))

    def test_binary_cannot_drift(self):
        self.reject(lambda w:w[0]['samples'][0]['command'].__setitem__(0,'/tmp/unreviewed-cli'))

    def test_unannotated_workload_cannot_enable_dictionary(self):
        self.reject(lambda w:w[0]['samples'][0]['command'].extend(['--dictionary',self.dictionary]))

    def test_failed_command_cannot_be_counted(self):
        self.reject(lambda w:w[0]['samples'][0].__setitem__('exit_code',1))

    def test_nonfinite_or_negative_time_cannot_be_counted(self):
        for value in [-1,float('inf'),float('nan'),True]:
            with self.subTest(value=value):
                self.reject(lambda w:w[0]['samples'][0].__setitem__('seconds',value))

    def test_summary_cannot_hide_a_slow_run(self):
        self.reject(lambda w:w[0]['summary']['before'].__setitem__('max_seconds',0))

    def test_rss_cannot_be_omitted(self):
        self.reject(lambda w:w[0]['samples'][0].__setitem__('peak_rss_kib',0))


class ReleaseTimingGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(ROOT/'docs/literary-question-go-performance.json')
        cls.cached_read = staticmethod(lru_cache(maxsize=None)(audit.read))

    def setUp(self):
        self.read_patch = patch.object(audit,'read',self.cached_read)
        self.read_patch.start()
        self.addCleanup(self.read_patch.stop)

    def reject(self, mutate):
        report = copy.deepcopy(self.report)
        mutate(report)
        with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration)):
            audit.inspect(report)

    def test_actual_release_timings_and_all_cache_streams_pass(self):
        self.assertEqual(audit.inspect(self.report)['cache_streams'],6)

    def test_running_capture_cannot_certify_performance(self):
        self.reject(lambda r:r.__setitem__('state','running'))

    def test_changed_producer_cannot_certify_capture_with_new_self_hash(self):
        def mutate(report):
            report['producer']['text'] += '\n# changed producer\n'
            report['producer']['sha256'] = audit.sha(report['producer']['text'].encode())
        self.reject(mutate)

    def test_another_package_receipt_cannot_certify_current_timings(self):
        self.reject(lambda r:r.__setitem__('package_sha256','0'*64))

    def test_cpu_affinity_cannot_expand(self):
        self.reject(lambda r:r['cpu_affinity'].append(r['cpu_affinity'][0]+1))

    def test_another_dictionary_cannot_certify_current_timings(self):
        self.reject(lambda r:r.__setitem__('dictionary_sha256','0'*64))

    def test_cache_mode_cannot_disappear(self):
        self.reject(lambda r:r['cache_parity'].pop())

    def test_cached_output_cannot_drift(self):
        self.reject(lambda r:r['cache_parity'][0]['checks'][1].__setitem__('sha256','0'*64))

    def test_compatible_mode_cannot_use_headword_filter(self):
        def mutate(report):
            row = report['cache_parity'][2]['checks'][0]
            row['command'][row['command'].index('--dict-compatible')] = '--dict-only'
        self.reject(mutate)

    def test_complete_novel_stream_cannot_shrink(self):
        self.reject(lambda r:r['cache_parity'][0]['checks'][0].__setitem__('records',179111))


if __name__=='__main__':
    unittest.main()
