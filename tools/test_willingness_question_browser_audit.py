"""Reject missing original browser alternatives, exports and Native ownership."""
import unittest
from unittest.mock import patch

import willingness_question_browser_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = audit.inputs()

    def reject(self, obj, updates, reason):
        with patch.dict(obj, updates):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(self.v)

    def test_complete_original_browser(self):
        result = audit.inspect(self.v)
        self.assertEqual((result['decisions'], result['exports'], result['native_owners']), (90, 6, 29))
        self.assertFalse(result['installed_new_family_verified'])
        self.assertFalse(result['full_coverage_complete'])

    def test_nonterminal_build(self):
        self.reject(self.v['build'], {'state': 'running'}, 'terminal frozen prototype build')

    def test_changed_prior_cli(self):
        self.reject(self.v['build'], {'prior_binaries_unchanged': False}, 'terminal frozen prototype build')

    def test_server_not_stopped(self):
        self.reject(self.v['runtime'], {'server_stopped': False}, 'terminal stopped prototype browser server')

    def test_unexpected_server_exit(self):
        self.reject(self.v['runtime'], {'server_exit_code': -9}, 'expected owned server shutdown')

    def test_wrong_actual_server(self):
        command = self.v['runtime']['command']
        self.reject(self.v['runtime'], {'command': ['invented', *command[1:]]}, 'actual source-bound server command')

    def test_missing_frontend_asset(self):
        self.reject(self.v['runtime'], {'frozen_inputs': {k: v for k, v in self.v['runtime']['frozen_inputs'].items() if not k.endswith('index.html')}}, 'all actual built frontend asset bytes')

    def test_erased_source_case(self):
        self.reject(self.v, {'suites': self.v['suites'][:1]}, 'all independent source and boundary paths')

    def test_missing_unicode_export(self):
        self.reject(self.v['browser'], {'exports': self.v['browser']['exports'][:-1]}, 'all six original browser exports')

    def test_erased_export_alternative(self):
        analysis = self.v['browser']['exports'][0]['records'][0]['analysis']
        self.reject(analysis, {'analyses': analysis['analyses'][:-1]}, 'every independently filtered complete export')

    def test_original_unicode_span(self):
        span = self.v['browser']['responses'][1]['api']['records'][0]['span']
        self.reject(span, {'start': 1}, 'all original browser input bytes and spans')

    def test_wrong_dropdown_policy(self):
        self.reject(self.v['browser']['policyDecisions'][0], {'offered_indices': []}, 'all original reading dropdown policies')

    def test_wrong_diagram_order(self):
        diagram = self.v['browser']['diagrams'][0]
        self.reject(diagram, {'forms': list(reversed(diagram['forms']))}, 'all independently typed display components and order')

    def test_expression_owner_not_an_ending(self):
        self.reject(self.v['label'], {'sources': [{'id': 86640, 'headword': '-련', 'pos': '품사 없음'}]}, 'ending owners remain separate from expression homonyms')

    def test_wrong_source_hint(self):
        self.reject(self.v['browser']['diagrams'][0], {'source_hint': 'invented'}, 'original ending source ownership displayed')

    def test_lost_native_homonym(self):
        self.reject(self.v['browser'], {'nativeEntries': self.v['browser']['nativeEntries'][:-1]}, 'every complete original Native endpoint field')

    def test_changed_native_sense(self):
        self.reject(self.v['browser']['nativeEntries'][0]['entry'], {'senses': []}, 'every complete original Native endpoint field')


if __name__ == '__main__':
    unittest.main()
