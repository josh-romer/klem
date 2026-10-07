"""Reject incomplete or altered captures of actual contrast-ending executions."""
import copy
import unittest
from functools import lru_cache
from unittest.mock import patch

import declarative_contrast_runtime as audit

cached_read = lru_cache(maxsize=None)(audit.read)

class RuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = audit.read(audit.ROOT/'docs/declarative-contrast-main-cli-replay-retry1.json')
        cls.adapter = audit.read(audit.ROOT/'docs/declarative-contrast-main-adapter-replay.json.gz')
        cls.browser = audit.read(audit.ROOT/'docs/declarative-contrast-main-browser.json')

    def setUp(self):
        self.read_patch = patch.object(audit, 'read', cached_read)
        self.read_patch.start()
        self.addCleanup(self.read_patch.stop)

    def reject(self, kind, mutate):
        report = copy.deepcopy(getattr(self, kind))
        mutate(report)
        with self.assertRaises((AssertionError, KeyError, ValueError, StopIteration)):
            if kind == 'browser':
                audit.verify_browser(report, self.cli)
            else:
                getattr(audit, 'verify_'+kind)(report)

    def test_actual_main_captures_pass(self):
        self.assertEqual(audit.verify_cli(self.cli)['corpus_words'], 32096)
        self.assertEqual(audit.verify_adapter(self.adapter), 66570)
        self.assertEqual(audit.verify_browser(self.browser, self.cli)['native_entries'], 115)

    def test_changed_producer_cannot_certify_capture_with_new_self_hash(self):
        def mutate(report):
            report['producer']['text'] += '\n# changed producer\n'
            report['producer']['sha256'] = audit.sha(report['producer']['text'].encode())
        self.reject('cli', mutate)

    def test_frozen_binary_identity_cannot_drift(self):
        self.reject('cli', lambda r:r.__setitem__('cli_sha256', '0'*64))

    def test_source_stream_cannot_be_replaced(self):
        self.reject('cli', lambda r:r['runs'].__setitem__(1, r['runs'][0]))

    def test_individual_forbidden_judgment_cannot_be_relabeled(self):
        def mutate(report):
            row = next(r for r in report['judgments'] if r['verdict']=='forbidden')
            row.update(verdict='required', present=True)
        self.reject('cli', mutate)

    def test_broad_stream_cannot_disappear(self):
        self.reject('cli', lambda r:r['broad'].pop())

    def test_corpus_output_digest_cannot_drift(self):
        self.reject('cli', lambda r:r['corpora'].__setitem__('word_analyses_sha256', '0'*64))

    def test_contextual_correctness_cannot_be_inferred_from_parity(self):
        self.reject('cli', lambda r:r.__setitem__('contextual_verdict', 'correct'))

    def test_original_gold_row_count_cannot_shrink(self):
        self.reject('adapter', lambda r:r['runs'][0].__setitem__('rows', 0))

    def test_adapter_cannot_claim_unbound_rows(self):
        self.reject('adapter', lambda r:r['runs'][0].__setitem__('all_rows_independently_bound_to_word_analyses', False))

    def test_api_source_frame_cannot_disappear(self):
        self.reject('browser', lambda r:r['responses'][0]['after']['records'].pop())

    def test_exported_candidate_cannot_disappear(self):
        def mutate(report):
            row = next(r for r in report['exports'][0]['records'] if r.get('analysis'))
            row['analysis']['analyses'] = []
        self.reject('browser', mutate)

    def test_whole_ending_diagram_cannot_be_relabeled_as_particle(self):
        self.reject('browser', lambda r:r['diagrams'][0]['pieces'][0].__setitem__('label', 'Particle'))

    def test_native_metadata_cannot_disappear(self):
        self.reject('browser', lambda r:r['native'][0]['response']['entry'].__setitem__('senses', []))

    def test_original_source_pane_cannot_disappear(self):
        self.reject('browser', lambda r:r['opened'].pop())

    def test_browser_errors_cannot_be_ignored(self):
        self.reject('browser', lambda r:r['errors'].append('uncaught error'))

    def test_only_finite_nonnegative_api_elapsed_time_is_ignored(self):
        for value in [-1, float('nan'), float('inf'), True]:
            with self.subTest(value=value):
                self.reject('browser', lambda r:r['responses'][0]['after'].__setitem__('elapsed_ms', value))


class PackageGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = {'package':'declarative-contrast-package-nix.json',
                 'cli':'declarative-contrast-packaged-cli-replay.json',
                 'adapter':'declarative-contrast-packaged-adapter-replay.json.gz',
                 'browser':'declarative-contrast-packaged-browser.json',
                 'auxiliary':'declarative-contrast-auxiliary-nix.json',
                 'launcher':'declarative-contrast-web-launcher.json'}
        cls.reports = {key:cached_read(audit.ROOT/'docs'/name) for key,name in names.items()}

    def setUp(self):
        self.read_patch = patch.object(audit,'read',cached_read)
        self.read_patch.start()
        self.addCleanup(self.read_patch.stop)

    def reject(self, key, mutate):
        reports = dict(self.reports)
        reports[key] = copy.deepcopy(reports[key])
        mutate(reports[key])
        with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration)):
            audit.verify_package(**reports)

    def test_actual_package_adapter_browser_and_launcher_pass(self):
        result = audit.verify_package(**self.reports)
        self.assertEqual(result['adapter_rows'],66570)
        self.assertEqual(result['launcher']['source_api_frames'],1012)

    def test_running_build_cannot_certify_package(self):
        self.reject('package',lambda r:r.__setitem__('state','running'))

    def test_source_file_hash_cannot_drift(self):
        self.reject('package',lambda r:r['snapshot']['files']['src/engine.rs'].__setitem__('sha256','0'*64))

    def test_adapter_cannot_claim_different_library_source(self):
        self.reject('auxiliary',lambda r:r.__setitem__('source','/nix/store/unrelated-source'))

    def test_adapter_cannot_bind_an_older_package_receipt(self):
        self.reject('auxiliary',lambda r:r.__setitem__('main_package_receipt_sha256','0'*64))

    def test_adapter_binary_cannot_be_replaced_by_main_cli(self):
        self.reject('adapter',lambda r:r.__setitem__('adapter',self.reports['cli']['cli']))

    def test_browser_cannot_use_another_cli(self):
        self.reject('browser',lambda r:r.__setitem__('cli_sha256','0'*64))

    def test_launcher_cannot_default_to_older_assets_even_with_new_hash(self):
        def mutate(report):
            report['launcher_text'] = report['launcher_text'].replace(report['assets'],'/nix/store/older-assets/share/klem-web')
            report['launcher_sha256'] = audit.sha(report['launcher_text'].encode())
        self.reject('launcher',mutate)

    def test_launcher_source_response_cannot_drop_a_candidate(self):
        def mutate(report):
            row = next(r for r in report['responses'][0]['after']['records'] if r.get('analysis'))
            row['analysis']['analyses'].pop()
        self.reject('launcher',mutate)

    def test_launcher_cannot_skip_packaged_css(self):
        self.reject('launcher',lambda r:r['asset_checks'].pop())


if __name__ == '__main__':
    unittest.main()
