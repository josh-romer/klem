"""Reject incomplete or altered captures of actual ostensible-reason executions."""
import copy
import unittest
from functools import lru_cache
from unittest.mock import patch

import ostensible_reason_runtime as audit

cached_read = lru_cache(maxsize=None)(audit.read)

class RuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = audit.read(audit.ROOT/'docs/ostensible-reason-main-cli-replay-retry1.json')
        cls.adapter = audit.read(audit.ROOT/'docs/ostensible-reason-main-adapter-replay.json.gz')
        cls.browser = audit.read(audit.ROOT/'docs/ostensible-reason-main-browser.json')

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
        self.assertEqual(audit.verify_browser(self.browser, self.cli)['native_entries'], 91)

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

    def test_conditional_unknown_cannot_become_compatible(self):
        def mutate(report):
            row = next(r for r in report['conditionalExports'][0]['records']
                       if r.get('analysis') and r['analysis']['normalized']=='학생이답시고')
            changes = 0
            for reading in row['dictionary']['readings']:
                for slot in reading['lemmas']:
                    for entry in slot['entries']:
                        if entry['id']=='krdict:86232' and entry['status']=='unknown':
                            entry['status']='compatible'
                            changes += 1
            assert changes
        self.reject('browser',mutate)

    def test_dictionary_free_hypothesis_cannot_be_globally_forbidden(self):
        def mutate(report):
            row = next(r for r in report['conditional_observations']
                       if r['case']=='ostensible-reason-mode-bare-verb-conflict' and r['mode']=='raw')
            row.update(present=False,expected_presence=False,targets=[])
        self.reject('cli',mutate)

    def test_conditional_diagram_cannot_disappear(self):
        self.reject('browser',lambda r:r['conditionalDiagrams'].pop())

    def test_browser_errors_cannot_be_ignored(self):
        self.reject('browser', lambda r:r['errors'].append('uncaught error'))

    def test_only_finite_nonnegative_api_elapsed_time_is_ignored(self):
        for value in [-1, float('nan'), float('inf'), True]:
            with self.subTest(value=value):
                self.reject('browser', lambda r:r['responses'][0]['after'].__setitem__('elapsed_ms', value))


class ConditionalModeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli=cached_read(audit.ROOT/'docs/ostensible-reason-main-cli-replay-retry1.json')
        cls.mode=cached_read(audit.ROOT/'docs/ostensible-reason-main-mode-preservation.json.gz')

    def setUp(self):
        self.read_patch=patch.object(audit,'read',cached_read);self.read_patch.start();self.addCleanup(self.read_patch.stop)

    def reject(self,mutate):
        report=copy.deepcopy(self.mode);mutate(report)
        with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration)):
            audit.verify_mode_preservation(report,self.cli)

    def test_actual_conditional_preservation_and_unjudged_tracking_pass(self):
        self.assertEqual(audit.verify_mode_preservation(self.mode,self.cli)['individually_unjudged_additions'],120)

    def test_new_path_cannot_disappear(self):
        self.reject(lambda r:r['individual_additions'].pop())

    def test_unjudged_path_cannot_be_self_certified(self):
        self.reject(lambda r:r['individual_additions'][0].__setitem__('structural_verdict','required'))

    def test_prior_verified_binary_cannot_be_replaced(self):
        self.reject(lambda r:r.__setitem__('before_cli_sha256','0'*64))

    def test_native_owner_cannot_disappear(self):
        self.reject(lambda r:r['matched_native_owner_ids'].pop())

    def test_conditional_case_reference_cannot_change(self):
        self.reject(lambda r:r['individual_additions'][0]['conditional_assertion_refs'][0].__setitem__('case','invented'))


class PackagedRuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records={key:cached_read(audit.ROOT/path) for key,path in {
            'package':'docs/ostensible-reason-package-nix.json',
            'cli':'docs/ostensible-reason-packaged-cli-replay.json',
            'adapter':'docs/ostensible-reason-packaged-adapter-replay.json.gz',
            'browser':'docs/ostensible-reason-packaged-browser.json',
            'launcher':'docs/ostensible-reason-packaged-web-launcher.json'}.items()}

    def reject(self,kind,mutate):
        records=dict(self.records)
        records[kind]=copy.deepcopy(records[kind])
        mutate(records[kind])
        with patch.object(audit,'read',cached_read):
            with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration)):
                audit.verify_package(**records)

    def test_actual_independent_packages_pass(self):
        with patch.object(audit,'read',cached_read):
            self.assertEqual(audit.verify_package(**self.records)['adapter_rows'],66570)

    def test_running_package_cannot_certify_runtime(self):
        self.reject('package',lambda r:r.__setitem__('state','running'))

    def test_build_command_must_execute_all_three_actual_checks(self):
        self.reject('package',lambda r:r['command'].pop())

    def test_rewritten_package_producer_cannot_certify_capture(self):
        def mutate(report):
            report['producer']['text']+='\n# altered producer\n'
            report['producer']['sha256']=audit.sha(report['producer']['text'].encode())
        self.reject('package',mutate)

    def test_release_log_cannot_be_replaced(self):
        self.reject('package',lambda r:r.__setitem__('log_sha256','0'*64))

    def test_frozen_source_cannot_disappear(self):
        self.reject('package',lambda r:r['snapshot']['files'].popitem())

    def test_frozen_source_digest_cannot_change(self):
        self.reject('package',lambda r:r['snapshot']['files']['src/engine.rs'].__setitem__('sha256','0'*64))

    def test_adapter_cannot_use_different_source_profile(self):
        self.reject('package',lambda r:r['source_profiles'].__setitem__('corpus-adapter','/nix/store/unreviewed-source'))

    def test_prior_cli_cannot_substitute_for_new_package(self):
        self.reject('cli',lambda r:r.__setitem__('cli','/tmp/old-klem'))

    def test_prior_adapter_cannot_substitute_for_new_package(self):
        self.reject('adapter',lambda r:r.__setitem__('adapter','/tmp/old-adapter'))

    def test_prior_server_cannot_substitute_for_new_package(self):
        self.reject('launcher',lambda r:r.__setitem__('server','/tmp/old-server'))

    def test_browser_capture_cannot_be_replaced(self):
        self.reject('launcher',lambda r:r.__setitem__('browser_sha256','0'*64))

    def test_served_asset_cannot_disappear(self):
        self.reject('launcher',lambda r:r['asset_checks'].pop())

    def test_owned_server_must_be_stopped(self):
        self.reject('launcher',lambda r:r.__setitem__('server_stopped',False))

    def test_launcher_must_execute_reviewed_server_and_assets(self):
        def mutate(report):
            report['launcher_text']=report['launcher_text'].replace(report['server'],'/tmp/old-server')
            report['launcher_sha256']=audit.sha(report['launcher_text'].encode())
        self.reject('launcher',mutate)


if __name__=='__main__':
    unittest.main()
