"""Reject fabricated installed builds, missing original workloads and browser paths."""
import json
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import willingness_question_installed_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = audit.inputs()

    def reject(self, obj, updates, reason, section='families', sync_binding=False, sync_full_rust=False):
        with ExitStack() as stack:
            stack.enter_context(patch.dict(obj, updates))
            if sync_full_rust:
                full_raw = (json.dumps(self.v['full_rust'], ensure_ascii=False, indent=2) + '\n').encode()
                stack.enter_context(patch.dict(self.v, {'full_rust_raw': full_raw}))
                stack.enter_context(patch.dict(self.v['binding'], {'full_rust_input_receipt_sha256': audit.sha(full_raw)}))
                sync_binding = True
            if sync_binding:
                raw = (json.dumps(self.v['binding'], ensure_ascii=False, indent=2) + '\n').encode()
                stack.enter_context(patch.dict(self.v, {'binding_raw': raw}))
                stack.enter_context(patch.dict(self.v['release'], {'binding_sha256': audit.sha(raw)}))
            with self.assertRaisesRegex(AssertionError, reason):
                getattr(audit, 'inspect_' + section)(self.v)

    def test_complete_actual_installed_evidence(self):
        result = audit.inspect(self.v)
        self.assertEqual((result['source_frames'], result['import_native_owners'], result['browser_decisions']), (3336, 30, 90))
        self.assertFalse(result['full_coverage_complete'])
        self.assertFalse(result['contextual_review_complete'])

    def test_independent_distribution_source_changed(self):
        self.reject(self.v['selected_validation'], {'head': 'invented'}, 'same complete tracked source snapshot', 'source_evidence')

    def test_original_distribution_audit_log_erased(self):
        logs = list(self.v['selected_logs']); logs[2] = b'invented'
        self.reject(self.v, {'selected_logs': logs}, 'actual independent audit logs', 'source_evidence')

    def test_original_distribution_control_count_weakened(self):
        self.reject(self.v['selected_validation']['runs'][3], {'controls': 1}, 'actual independent audit logs', 'source_evidence')

    def test_nonterminal_packages(self):
        self.reject(self.v['binding'], {'state': 'running'}, 'terminal installed packages', 'binding')

    def test_changed_package_inputs(self):
        self.reject(self.v['binding'], {'all_tracked_inputs_unchanged': False}, 'frozen installed package inputs', 'binding')

    def test_changed_binding_receipt(self):
        self.reject(self.v, {'binding_raw': b'invented'}, 'unchanged binding receipt', 'binding')

    def test_incomplete_actual_selected_profile(self):
        p = self.v['binding']['profiles']['klem']
        self.reject(p, {'files': dict(list(p['files'].items())[:-1])}, 'complete actual package profiles', 'binding', True)

    def test_changed_actual_derivation_capture(self):
        p = self.v['binding']['profiles']['klem']
        self.reject(p, {'derivation_json_sha256': '0' * 64}, 'actual derivation capture', 'binding', True)

    def test_wrong_tracked_source_digest(self):
        p = next(iter(self.v['binding']['profiles']['klem']['files'].values()))
        self.reject(self.v['binding']['all_tracked_files'], {p['snapshot_path']: '0' * 64}, 'every selected file bound', 'binding', True)

    def test_wrong_launcher_server(self):
        launcher = self.v['binding']['launcher']
        text = launcher['text'].replace(self.v['binding']['profiles']['klem']['package'], '/invented')
        self.reject(launcher, {'text': text, 'sha256': audit.sha(text.encode())}, 'bound server and assets', 'binding', True)

    def test_changed_release_log(self):
        self.reject(self.v, {'release_log': b'invented passing tests'}, 'actual installed release log', 'binding')

    def test_wrong_release_derivation(self):
        self.reject(self.v['release'], {'derivation': '/invented'}, 'same installed release derivation', 'binding')

    def test_missing_release_batch(self):
        self.reject(self.v['release'], {'batches': 251}, 'complete actual release tests', 'binding')

    def test_nonterminal_debug_rust_receipt(self):
        self.reject(self.v['full_rust'], {'state': 'running'}, 'terminal frozen debug Rust receipt', 'binding')

    def test_changed_debug_rust_receipt_bytes(self):
        self.reject(self.v, {'full_rust_raw': b'invented'}, 'actual debug Rust receipt', 'binding')

    def test_coordinated_debug_runtime_source_digest(self):
        keys = self.v['full_rust']['frozen_inputs']
        name = '/tmp/klem-willingness-question-prototype/src/engine.rs'
        self.reject(keys, {name: '0' * 64}, 'actual shared debug Rust input bytes', 'binding', sync_full_rust=True)

    def test_missing_family(self):
        self.reject(self.v, {'families': {k: v for k, v in self.v['families'].items() if k != 'gold'}}, 'all four installed workload families')

    def test_missing_unicode_cache_stream(self):
        report = self.v['families']['source']
        self.reject(report, {'runs': report['runs'][:-1]}, 'complete installed workload runs')

    def test_wrong_workload_binding(self):
        self.reject(self.v['families']['source'], {'binding_sha256': '0' * 64}, 'same installed workload binding')

    def test_finite_output_digest(self):
        self.reject(self.v['families']['source']['runs'][0], {'stdout_sha256': '0' * 64}, 'every complete finite output')

    def test_finite_filter_command(self):
        run = next(r for r in self.v['families']['source']['runs'] if r['mode'] == 'headword')
        self.reject(run, {'command': [arg for arg in run['command'] if arg != '--dict-only']}, 'actual finite filter command')

    def test_missing_original_cohort_word(self):
        run = self.v['families']['cohorts']['runs'][0]
        self.reject(run, {'surfaces': run['surfaces'] - 1}, 'complete original cohort identity')

    def test_changed_cohort_path_digest(self):
        self.reject(self.v['families']['cohorts']['runs'][0], {'actual_words_sha256': '0' * 64}, 'every complete cohort word')

    def test_wrong_gold_adapter(self):
        run = self.v['families']['gold']['runs'][0]
        self.reject(run, {'command': ['/invented', *run['command'][1:]]}, 'actual annotated adapter command')

    def test_changed_original_gold_summary(self):
        self.reject(self.v['families']['gold']['runs'][0], {'stdout_sha256': '0' * 64}, 'every complete annotated row and summary')

    def test_erased_individual_novel_observation(self):
        run = next(r for r in self.v['families']['broad']['runs'] if r['all_individual_changed_records_exact'])
        self.reject(run, {'all_individual_changed_records_exact': 0}, 'every complete broad output')

    def test_missing_broad_spacing_flag(self):
        run = next(r for r in self.v['families']['broad']['runs'] if 'spacing' in r['mode'])
        self.reject(run, {'command': run['command'][:-1]}, 'actual broad filter spacing command')

    def test_imported_native_field_fabricated(self):
        entry = next(iter(self.v['families']['source']['native_import']['complete_imported_entries'].values()))
        self.reject(entry, {'pos': 'invented'}, 'every complete original imported Native field')

    def test_supplemental_native_owner_erased(self):
        imported = self.v['families']['source']['native_import']
        self.reject(imported, {'complete_imported_entries': {k: e for k, e in imported['complete_imported_entries'].items() if k in self.v['native']}}, 'every complete original imported Native field')

    def test_wrong_importer_command(self):
        imported = self.v['families']['source']['native_import']
        self.reject(imported, {'command': ['/invented', *imported['command'][1:]]}, 'actual installed Native importer command')

    def test_missing_native_query(self):
        imported = self.v['families']['source']['native_import']
        self.reject(imported, {'entry_queries': imported['entry_queries'][:-1]}, 'every original Native query command')

    def test_live_browser_server(self):
        self.reject(self.v['runtime'], {'server_stopped': False}, 'owned installed server stopped', 'browser')

    def test_unexpected_browser_shutdown(self):
        self.reject(self.v['runtime'], {'server_exit_code': -9}, 'owned installed server stopped', 'browser')

    def test_wrong_browser_launcher(self):
        command = self.v['runtime']['command']
        self.reject(self.v['runtime'], {'command': ['/invented', *command[1:]]}, 'actual installed browser launcher', 'browser')

    def test_changed_browser_driver(self):
        self.reject(self.v, {'driver': b'invented'}, 'actual error-free installed browser', 'browser')

    def test_missing_browser_export(self):
        self.reject(self.v['browser'], {'exports': self.v['browser']['exports'][:-1]}, 'all six original browser exports', 'browser')

    def test_missing_browser_required_case(self):
        self.reject(self.v, {'suites': self.v['suites'][:1]}, 'all independent source and boundary paths', 'browser')

    def test_changed_browser_input_span(self):
        span = self.v['browser']['responses'][0]['api']['records'][0]['span']
        self.reject(span, {'start': 1}, 'all original browser input bytes and spans', 'browser')

    def test_erased_browser_export_path(self):
        record = self.v['browser']['exports'][0]['records'][0]
        self.reject(record['analysis'], {'analyses': record['analysis']['analyses'][:-1]}, 'every independently filtered complete export', 'browser')

    def test_changed_offered_indices(self):
        self.reject(self.v['browser']['policyDecisions'][0], {'offered_indices': []}, 'all original reading dropdown policies', 'browser')

    def test_changed_display_order(self):
        diagram = self.v['browser']['diagrams'][0]
        self.reject(diagram, {'forms': list(reversed(diagram['forms']))}, 'all independently typed display components and order', 'browser')

    def test_expression_owner_substituted(self):
        self.reject(self.v['label'], {'sources': [{'id': 86640, 'headword': '-련', 'pos': 'None'}]}, 'ending owners remain separate', 'browser')

    def test_browser_native_field_fabricated(self):
        entry = self.v['browser']['nativeEntries'][0]['entry']
        self.reject(entry, {'pos': 'invented'}, 'every complete original Native endpoint field', 'browser')


if __name__ == '__main__':
    unittest.main()
