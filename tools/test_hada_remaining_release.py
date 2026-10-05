"""Reject incomplete package, nested-owner, stream and timing evidence."""
import copy
import unittest

import hada_remaining_audit as audit
import hada_remaining_release as release
import hada_remaining_performance as performance


class ReleaseGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.read(release.REPORT)

    def test_complete_release(self):
        self.assertEqual(release.inspect(self.report)['rust_passed'], 946)

    def test_missing_cache_stream(self):
        report = copy.deepcopy(self.report)
        del report['runs']['compatible']['NFD-uncached']
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_incorrect_rust_receipt(self):
        report = copy.deepcopy(self.report)
        report['rust_passed'] = 938
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_missing_api_encoding(self):
        report = copy.deepcopy(self.report)
        report['api_batches'].pop()
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_only_elapsed_time_may_vary(self):
        report = copy.deepcopy(self.report)
        report['api_batches'][0]['response']['elapsed_ms'] += 1
        release.inspect(report)
        record = next(r for r in report['api_batches'][0]['response']['records'] if r.get('analysis'))
        record['analysis']['normalized'] = 'rewritten'
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_root_label_cannot_be_lexical_noun(self):
        report = copy.deepcopy(self.report)
        diagram = next(d for d in report['browser']['diagrams'] if d['source_owner']['base_role'] == 'root')
        diagram['formation_label'] = 'Noun formation'
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_nested_suffix_cannot_borrow_outer_class(self):
        report = copy.deepcopy(self.report)
        report['scoped_browser']['checks'][0]['labels'][0] = 'Auxiliary verb / adjective formation'
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_complete_native_entries_cannot_change(self):
        report = copy.deepcopy(self.report)
        report['complete_native_entries']['krdict:57643']['pos'] = '명사'
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_assets_receipt_cannot_be_replaced(self):
        report = copy.deepcopy(self.report)
        report['assets_nix_log']['text'] = 'unverified output'
        with self.assertRaises(AssertionError):
            release.inspect(report)


class TimingGuards(unittest.TestCase):
    def test_complete_timings(self):
        self.assertEqual(performance.inspect(audit.read(performance.REPORT)), 80)

    def test_missing_pair(self):
        report = audit.read(performance.REPORT)
        report['workloads'][0]['samples'].pop()
        with self.assertRaises(AssertionError):
            performance.inspect(report)

    def test_cache_output_must_match_package(self):
        report = audit.read(performance.REPORT)
        report['cli_sha256'] = 'forged'
        with self.assertRaises(AssertionError):
            performance.inspect(report)


if __name__ == '__main__':
    unittest.main()
