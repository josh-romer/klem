"""Reject missing workloads, altered Native fields and falsely offered browser paths."""
import unittest
from unittest.mock import patch

import conjectural_additive_installed_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = audit.inputs()

    def reject(self, obj, updates, reason):
        with patch.dict(obj, updates):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(self.v)

    def test_complete_installed_evidence(self):
        result = audit.inspect(self.v)
        self.assertEqual((result['finite_frames'], result['browser_decisions'], result['native_entries']), (57432, 288, 57))
        self.assertFalse(result['full_coverage_complete'])

    def test_nonterminal_packages(self):
        self.reject(self.v['binding'], {'state': 'running'}, 'terminal installed packages')

    def test_changed_package_inputs(self):
        self.reject(self.v['binding'], {'all_tracked_inputs_unchanged': False}, 'frozen installed package inputs')

    def test_altered_release_log(self):
        self.reject(self.v, {'release_log': b'invented passing tests'}, 'actual installed release log')

    def test_missing_family(self):
        self.reject(self.v, {'families': {k: v for k, v in self.v['families'].items() if k != 'novel'}}, 'all six installed families')

    def test_missing_unicode_cache_stream(self):
        report = self.v['families']['source']
        self.reject(report, {'runs': report['runs'][:-1]}, 'complete installed workload runs')

    def test_wrong_installed_binding(self):
        self.reject(self.v['families']['copula'], {'binding_sha256': '0' * 64}, 'same installed binding')

    def test_finite_output_digest(self):
        run = self.v['families']['novel']['runs'][0]
        self.reject(run, {'stdout_sha256': '0' * 64, 'reference_stdout_sha256': '0' * 64}, 'every complete finite output')

    def test_finite_filter_command(self):
        run = next(r for r in self.v['families']['source']['runs'] if r['mode'] == 'headword')
        command = [arg for arg in run['command'] if arg != '--dict-only']
        self.reject(run, {'command': command}, 'actual finite filter command')

    def test_missing_original_cohort_word(self):
        run = self.v['families']['cohorts']['runs'][0]
        self.reject(run, {'surfaces': run['surfaces'] - 1}, 'complete original cohort identity')

    def test_original_cohort_output(self):
        run = self.v['families']['cohorts']['runs'][1]
        self.reject(run, {'actual_words_sha256': '0' * 64}, 'every complete cohort word')

    def test_annotated_adapter_identity(self):
        run = self.v['families']['gold']['runs'][0]
        self.reject(run, {'command': ['fabricated', *run['command'][1:]]}, 'actual annotated adapter command')

    def test_annotated_summary_output(self):
        run = self.v['families']['gold']['runs'][0]
        self.reject(run, {'stdout_sha256': '0' * 64}, 'every complete annotated row and summary')

    def test_broad_individual_observation_erased(self):
        run = next(r for r in self.v['families']['broad']['runs'] if r['all_individual_changed_records_exact'])
        self.reject(run, {'all_individual_changed_records_exact': 0}, 'every complete broad output')

    def test_broad_spacing_flag(self):
        run = next(r for r in self.v['families']['broad']['runs'] if 'spacing' in r['mode'])
        self.reject(run, {'command': run['command'][:-1]}, 'actual broad filter spacing command')

    def test_server_still_running(self):
        self.reject(self.v['runtime'], {'server_stopped': False}, 'owned installed server stopped')

    def test_browser_launcher_identity(self):
        command = self.v['runtime']['command']
        self.reject(self.v['runtime'], {'command': ['fabricated', *command[1:]]}, 'actual installed browser launcher')

    def test_missing_browser_unicode_export(self):
        self.reject(self.v['browser'], {'exports': self.v['browser']['exports'][:-1]}, 'all six browser export choices')

    def test_altered_browser_span(self):
        span = self.v['browser']['responses'][0]['api']['records'][0]['span']
        self.reject(span, {'start': 1}, 'complete original browser bytes')

    def test_browser_export_erased_path(self):
        record = self.v['browser']['exports'][0]['records'][0]
        self.reject(record['analysis'], {'analyses': record['analysis']['analyses'][:-1]}, 'independently derived complete browser export')

    def test_missing_second_novel_alternative(self):
        case = next(c for c in self.v['suites'][2]['cases'] if len(c['judgments']) == 2)
        self.reject(case, {'judgments': case['judgments'][:1]}, 'all original independent browser paths')

    def test_browser_offered_indices(self):
        decision = self.v['browser']['policyDecisions'][0]
        self.reject(decision, {'offered_indices': []}, 'every independently derived browser policy')

    def test_browser_morpheme_order(self):
        diagram = self.v['browser']['diagrams'][0]
        self.reject(diagram, {'forms': list(reversed(diagram['forms']))}, 'every independent typed component order')

    def test_browser_source_owner_erased(self):
        self.reject(self.v['browser']['diagrams'][0], {'source_hint': 'fabricated'}, 'original grammar label owners')

    def test_browser_native_pos_fabricated(self):
        entry = self.v['browser']['nativeEntries'][0]['entry']
        self.reject(entry, {'pos': 'invented'}, 'every original Native endpoint field')


if __name__ == '__main__':
    unittest.main()
