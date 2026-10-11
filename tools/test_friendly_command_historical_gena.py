"""Keep old command IDs scoped while requiring the complete current Gena guard."""
import ast
import copy
import json
import unittest
from unittest.mock import patch

import friendly_command_audit as legacy
import friendly_command_gena_ledger_audit as gena


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = gena.inputs()
        cls.raw = cls.values['current_raw']

    def changed(self, change):
        values = copy.copy(self.values)
        data = json.loads(self.raw)
        change(data)
        values['current_raw'] = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
        return values

    def reject(self, values, message):
        with patch.object(gena, 'inputs', return_value=values):
            with self.assertRaisesRegex(AssertionError, message):
                legacy.command_ledger(values['current_raw'])

    def test_complete_current_guard_precedes_exact_parent_view(self):
        with patch.object(gena, 'inspect', wraps=gena.inspect) as guard:
            parent = legacy.command_ledger(self.raw)
        guard.assert_called_once()
        self.assertEqual(guard.call_args.args[0]['current_raw'], self.raw)
        self.assertEqual(parent, json.loads(self.values['parent_raw']))
        fixture = legacy.read(legacy.ROOT / 'tests/fixtures/friendly-command-sources.json')
        self.assertEqual([c for c in parent['cases'] if c['id'].startswith('friendly-command-')], fixture['cases'])
        self.assertEqual(len(fixture['cases']), 7)

    def test_original_parent_does_not_require_a_descendant(self):
        with patch.object(gena, 'inspect') as guard:
            parent = legacy.command_ledger(self.values['parent_raw'])
        guard.assert_not_called()
        self.assertEqual(parent, json.loads(self.values['parent_raw']))

    def test_missing_gena_case_rejected(self):
        self.reject(self.changed(lambda r: r['cases'].pop()), 'complete35740 parent plus24 cases')

    def test_extra_unjudged_tail_rejected(self):
        def change(data):
            case = copy.deepcopy(data['cases'][-1]); case['id'] = 'unjudged-tail'; data['cases'].append(case)
        self.reject(self.changed(change), 'complete35740 parent plus24 cases')

    def test_renamed_gena_prefix_cannot_hide_the_tail(self):
        def change(data):
            for index, case in enumerate(data['cases'][35740:]): case['id'] = 'unrelated-prefix-' + str(index)
        self.reject(self.changed(change), 'only exact24 preauthored cases appended')

    def test_changed_original_command_case_rejected(self):
        def change(data):
            next(c for c in data['cases'][:35740] if c['id'].startswith('friendly-command-'))['surface'] = 'changed'
        self.reject(self.changed(change), 'every old case field and relative order')

    def test_borrowed_current_ledger_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'complete current command ledger matches guarded Gena source'):
            legacy.command_ledger(self.changed(lambda r: r['cases'][-1].update(surface='changed'))['current_raw'])

    def test_old_family_prefix_assertion_is_still_present(self):
        tree = ast.parse((legacy.ROOT / 'tools/friendly_command_audit.py').read_text())
        assertions = [ast.unparse(node) for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        self.assertIn("assert [c for c in ledger['cases'] if c['id'].startswith('friendly-command-')] == f['cases']", assertions)


if __name__ == '__main__': unittest.main()
