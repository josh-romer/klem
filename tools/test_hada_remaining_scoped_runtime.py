"""Guard against borrowing another suffix's class or erasing past alternatives."""
import copy
import unittest

import hada_remaining_scoped_runtime as audit


class ScopedGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.read(audit.REPORT)

    def test_complete_scoped_diagrams(self):
        self.assertEqual(audit.inspect(self.report), 6)

    def test_bare_present_cannot_borrow_outer_adjective(self):
        report = copy.deepcopy(self.report)
        report['checks'][0]['labels'][0] = 'Auxiliary verb / adjective formation'
        with self.assertRaises(AssertionError):
            audit.inspect(report)

    def test_past_prefinal_keeps_both_classes(self):
        report = copy.deepcopy(self.report)
        check = next(c for c in report['checks'] if '했던' in c['request']['text'])
        check['labels'][0] = 'Auxiliary verb formation'
        with self.assertRaises(AssertionError):
            audit.inspect(report)

    def test_api_must_match_actual_cli(self):
        report = copy.deepcopy(self.report)
        report['checks'][0]['cli_records'] = []
        with self.assertRaises(AssertionError):
            audit.inspect(report)

    def test_current_frontend_has_exact_original_source_parent(self):
        text = (audit.ROOT / 'web/src/breakdown.ts').read_bytes().decode('utf8')
        self.assertEqual(audit.frontend_parent_sha(text), self.report['frontend_sha256'])

    def test_unrelated_suffix_label_change_cannot_borrow_command_inverse(self):
        text = (audit.ROOT / 'web/src/breakdown.ts').read_bytes().decode('utf8')
        changed = text.replace('Auxiliary adjective formation', 'Unscoped adjective formation', 1)
        self.assertNotEqual(changed, text)
        self.assertNotEqual(audit.frontend_parent_sha(changed), self.report['frontend_sha256'])

    def test_missing_source_selection_edit_is_not_an_exact_inverse(self):
        text = (audit.ROOT / 'web/src/breakdown.ts').read_bytes().decode('utf8')
        changed = text.replace('(attachedN ? undefined : entries[0])', 'entries[0]', 1)
        with self.assertRaises(AssertionError):
            audit.frontend_parent_sha(changed)


if __name__ == '__main__':
    unittest.main()
