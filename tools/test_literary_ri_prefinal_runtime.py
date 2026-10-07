"""Reject forged replay completion, missing cases, and drifted stream hashes."""
import copy
import unittest

import literary_ri_prefinal_runtime as a


class ReplayGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = a.read(a.BASE / 'literary-ri-prefinal-main-cli-replay.json.gz')
        cls.adapter = a.read(a.BASE / 'literary-ri-prefinal-main-adapter-replay.json.gz')

    def reject_cli(self, change):
        report = copy.deepcopy(self.cli)
        change(report)
        with self.assertRaises((AssertionError, KeyError, ValueError)):
            a.verify_cli(report)

    def test_complete_actual_main_replay(self):
        self.assertEqual(a.verify_cli(self.cli)['broad_frames'], 1128312)
        self.assertEqual(a.verify_adapter(self.adapter), 66570)

    def test_running_receipt_cannot_certify_completion(self):
        self.reject_cli(lambda d: d.__setitem__('state', 'running'))

    def test_positive_b_counterpart_cannot_disappear(self):
        self.reject_cli(lambda d: d['probes'].pop())

    def test_duplicate_probe_cannot_replace_nfd_compatible_case(self):
        self.reject_cli(lambda d: d['probes'].__setitem__(-1, d['probes'][0]))

    def test_raw_provider_hypothesis_cannot_become_global_ban(self):
        def change(report):
            probe = next(r for r in report['probes'] if r['case'] == 'literary-ri-prefinal-boundary-3-니' and r['mode'] == 'raw')
            probe['observations'][0]['mode_verdict'] = 'forbidden'
        self.reject_cli(change)

    def test_old_broad_hash_cannot_replace_new_output(self):
        def change(report):
            original = a.read(a.BASE / 'literary-ri-prefinal-prototype-broad.json.gz')
            report['broad'][0]['sha256'] = original['comparisons'][0]['before_jsonl_sha256']
        self.reject_cli(change)

    def test_corpus_word_hash_cannot_change(self):
        self.reject_cli(lambda d: d['corpora'].__setitem__('word_analyses_sha256', '0' * 64))

    def test_actual_adapter_partition_cannot_disappear(self):
        report = copy.deepcopy(self.adapter)
        report['runs'].pop()
        with self.assertRaises(AssertionError):
            a.verify_adapter(report)

    def test_actual_adapter_hash_cannot_change(self):
        report = copy.deepcopy(self.adapter)
        report['runs'][0]['sha256'] = '0' * 64
        with self.assertRaises(AssertionError):
            a.verify_adapter(report)


class PackageGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = a.read(a.BASE / 'literary-ri-prefinal-package-nix.json')
        cls.cli = a.read(a.BASE / 'literary-ri-prefinal-packaged-cli-replay.json.gz')
        cls.browser = a.read(a.BASE / 'literary-ri-prefinal-packaged-browser.json')
        cls.hada = a.read(a.BASE / 'literary-ri-prefinal-packaged-hada-scoped-browser.json')

    def verify(self, package=None, browser=None, hada=None):
        return a.verify_package(package or self.package, self.cli,
                                browser or self.browser, hada or self.hada)

    def test_complete_actual_package(self):
        self.assertEqual(self.verify()['fresh_nested_hada_diagrams'], 6)

    def test_older_model_snapshot_cannot_certify_current_frontend(self):
        package = copy.deepcopy(self.package)
        package['snapshot']['files']['web/src/model.ts']['sha256'] = '0' * 64
        with self.assertRaises(AssertionError):
            self.verify(package=package)

    def test_older_package_hada_capture_cannot_certify_current_runtime(self):
        hada = copy.deepcopy(self.hada)
        hada['cli_sha256'] = a.read(a.BASE / 'double-past-prefinal-hada-scoped-browser.json')['cli_sha256']
        with self.assertRaises(AssertionError):
            self.verify(hada=hada)

    def test_nested_suffix_cannot_borrow_another_owner_class(self):
        hada = copy.deepcopy(self.hada)
        hada['checks'][0]['labels'][0] = 'Auxiliary verb / adjective formation'
        with self.assertRaises(AssertionError):
            self.verify(hada=hada)

    def test_api_candidate_cannot_disappear(self):
        browser = copy.deepcopy(self.browser)
        row = next(r for r in browser['responses'][0]['after']['records'] if r.get('analysis'))
        row['analysis']['analyses'].pop()
        with self.assertRaises(AssertionError):
            self.verify(browser=browser)

    def test_elapsed_time_is_the_only_ignored_api_field(self):
        runs = copy.deepcopy(self.browser['responses'])
        previous = copy.deepcopy(a.api_semantics(runs))
        runs[0]['after']['elapsed_ms'] += 100
        self.assertEqual(a.api_semantics(runs), previous)
        runs[0]['after']['records'].pop()
        self.assertTrue(a.api_semantics(runs) != previous)

    def test_invalid_elapsed_time_cannot_be_hidden(self):
        runs = copy.deepcopy(self.browser['responses'])
        runs[0]['after']['elapsed_ms'] = float('nan')
        with self.assertRaises(AssertionError):
            a.api_semantics(runs)


if __name__ == '__main__':
    unittest.main()
