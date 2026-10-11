"""Reject lost interaction paths, reversed auxiliary order and altered original Native data."""
import unittest
from unittest.mock import patch

import willingness_question_interaction_browser_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = audit.inputs()

    def reject(self, obj, updates, reason):
        with patch.dict(obj, updates):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(self.v)

    def test_complete_original_and_interaction_browser(self):
        result = audit.inspect(self.v)
        self.assertEqual((result['required_paths'], result['decisions'], result['native_owners']), (19, 114, 29))
        self.assertFalse(result['full_coverage_complete'])

    def test_new_cases_cannot_disappear(self):
        self.reject(self.v, {'suites': self.v['suites'][:2]}, 'all independent source and boundary paths')

    def test_old_source_cases_cannot_disappear(self):
        self.reject(self.v, {'suites': self.v['suites'][1:]}, 'all independent source and boundary paths')

    def test_wrong_installed_launcher(self):
        command = self.v['runtime']['command']
        self.reject(self.v['runtime'], {'command': ['/invented', *command[1:]]}, 'actual installed browser launcher')

    def test_server_must_stop(self):
        self.reject(self.v['runtime'], {'server_stopped': False}, 'owned installed server stopped')

    def test_wrong_driver(self):
        self.reject(self.v, {'driver': b'invented'}, 'actual error-free installed browser')

    def test_missing_unicode_export(self):
        self.reject(self.v['browser'], {'exports': self.v['browser']['exports'][:-1]}, 'all six original browser exports')

    def test_export_must_keep_auxiliary(self):
        record = next(r for r in self.v['browser']['exports'][0]['records'] if r['surface'] == '먹어주련')
        self.reject(record['analysis'], {'analyses': record['analysis']['analyses'][:-1]}, 'every independently filtered complete export')

    def test_auxiliary_display_order_cannot_reverse(self):
        diagram = next(d for d in self.v['browser']['diagrams'] if 'interaction-benefactive/' in d['case_id'])
        self.reject(diagram, {'forms': list(reversed(diagram['forms']))}, 'all independently typed display components and order')

    def test_irregular_display_cannot_borrow_regular_head(self):
        diagram = next(d for d in self.v['browser']['diagrams'] if 'interaction-d-full/' in d['case_id'])
        self.reject(diagram, {'forms': ['걸', '으련']}, 'all independently typed display components and order')

    def test_offered_paths_cannot_disappear(self):
        decision = next(d for d in self.v['browser']['policyDecisions'] if 'interaction-negative/' in d['case_id'])
        self.reject(decision, {'offered_indices': []}, 'all original reading dropdown policies')

    def test_sources_cannot_claim_expression_ownership(self):
        self.reject(self.v['label'], {'sources': [{'id': 86640, 'headword': '-련', 'pos': 'None'}]}, 'ending owners remain separate')

    def test_native_fields_cannot_be_rewritten(self):
        entry = self.v['browser']['nativeEntries'][0]['entry']
        self.reject(entry, {'pos': 'invented'}, 'every complete original Native endpoint field')

    def test_incomplete_rust_validation_cannot_bind_the_browser(self):
        self.reject(self.v['full_rust'], {'state': 'running'}, 'complete frozen interaction Rust validation')

    def test_wrong_complete_rust_scope_is_rejected(self):
        self.reject(self.v['full_rust'], {'totals': {'passed': 1174, 'failed': 0, 'ignored': 1}}, 'complete interaction Rust totals')

    def test_changed_production_file_cannot_use_parent_installed_proof(self):
        self.reject(self.v['full_rust']['frozen_inputs'], {'/tmp/klem-willingness-interactions/src/lib.rs': 'invented'}, 'only three inherited compiled-test files differ')

    def test_new_fixture_cannot_be_confused_with_the_parent_compiled_profile(self):
        self.reject(self.v['full_rust']['frozen_inputs'], {'/tmp/klem-willingness-interactions/tests/fixtures/willingness-question-interaction-validity.json': 'invented'}, 'exact new interaction fixture outside the inherited package profile')


if __name__ == '__main__':
    unittest.main()
