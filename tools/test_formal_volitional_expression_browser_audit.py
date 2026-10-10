"""Reject incomplete browser evidence and incorrectly retained/excluded readings."""
import copy
import unittest

import formal_volitional_expression_browser_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.evidence)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_complete_distribution_capture(self):
        result = audit.inspect(*self.evidence)
        self.assertEqual((result['policy_decisions'], result['rendered_diagrams'], result['native_entries']), (48, 48, 16))

    def test_owned_server_stopped(self):
        self.reject(lambda v: v[1].update(server_stopped=False), 'owned browser runtime stopped')

    def test_unexpected_server_signal(self):
        self.reject(lambda v: v[1].update(server_exit_code=-9), 'expected owned server exit')

    def test_unexpected_server_failure(self):
        self.reject(lambda v: v[1].update(server_exit_code=1), 'expected owned server exit')

    def test_actual_driver_bytes(self):
        self.reject(lambda v: v[0].update(producer_sha256='0' * 64), 'actual browser driver bytes')

    def test_missing_unicode_response(self):
        self.reject(lambda v: v[0]['responses'].pop(), 'both original Unicode responses')

    def test_missing_api_frame(self):
        self.reject(lambda v: v[0]['responses'][0]['api']['records'].pop(), 'complete original API frames')

    def test_original_byte_gap(self):
        self.reject(lambda v: v[0]['responses'][0]['api']['records'][0]['span'].update(start=1), 'original API span continuity')

    def test_missing_export(self):
        self.reject(lambda v: v[0]['exports'].pop(), 'six exact export choices')

    def test_filtered_export_not_raw(self):
        def mutate(v):
            v[0]['exports'][1]['records'] = copy.deepcopy(v[0]['exports'][0]['records'])
        self.reject(mutate, 'independently derived complete export')

    def test_missing_policy_decision(self):
        self.reject(lambda v: v[0]['policyDecisions'].pop(), 'all independent policy decisions')

    def test_original_selected_path_index(self):
        self.reject(lambda v: v[0]['policyDecisions'][0].update(raw_analysis_index=999), 'all independent policy decisions')

    def test_supported_path_not_hidden(self):
        self.reject(lambda v: v[0]['policyDecisions'][0].update(allowed=False), 'all independent policy decisions')

    def test_offered_indices_preserved(self):
        self.reject(lambda v: v[0]['policyDecisions'][0].update(offered_indices=['999']), 'all independent policy decisions')

    def test_missing_authored_diagram(self):
        self.reject(lambda v: v[0]['diagrams'].pop(), 'every exact authored diagram and form')

    def test_actual_diagram_component(self):
        self.reject(lambda v: v[0]['diagrams'][0]['forms'].__setitem__(0, 'fabricated'), 'every exact authored diagram and form')

    def test_source_label_identity(self):
        self.reject(lambda v: v[0]['diagrams'][0].update(source_hint='invented'), 'actual kind and original label owners')

    def test_complete_native_fields(self):
        self.reject(lambda v: v[0]['nativeEntries'][0]['entry'].update(headword='invented'), 'all complete original Native responses')

    def test_native_owner_missing(self):
        self.reject(lambda v: v[0]['nativeEntries'].pop(), 'all complete original Native responses')


if __name__ == '__main__':
    unittest.main()
