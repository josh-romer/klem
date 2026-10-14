"""Reject incomplete, borrowed, or rewritten parent evidence before projection."""
import copy
import unittest

import friendly_hortative_sena_gena_parent_audit as audit
import friendly_hortative_sena_revision as revision


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()
        original = revision.inputs()
        cls.current = original['actual_current_profiles']
        cls.previous = {name:row['files'] for name,row in original['selected']['friendly-hortative-sena-wide-selected-source.json']['profiles'].items()}
        cls.production = original['browser']['runtime']['binding']['production_inputs']

    def reject(self, path, change, reason):
        v = self.values.copy(); node = v
        for key in path[:-1]:
            node[key] = copy.copy(node[key]); node = node[key]
        node[path[-1]] = copy.deepcopy(node[path[-1]])
        change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(v, self.current, self.previous, self.production)

    def test_complete_actual_parent_and_exact_projection(self):
        report = audit.inspect(self.values, self.current, self.previous, self.production)
        self.assertEqual(report['full_rust_tests'], 1212)
        self.assertFalse(report['original25_Sena_cases_promoted'])
        self.assertEqual(audit.historical_profiles(self.values, self.current, self.previous, self.production), self.previous)
        self.assertNotEqual(self.current['klem']['tests/fixtures/validity.json'], self.previous['klem']['tests/fixtures/validity.json'])

    def test_running_rust_cannot_authorize_projection(self):
        self.reject(('rust',), lambda r:r.update(state='running'), 'actual complete parent Rust validation must pass')

    def test_failed_rust_cannot_authorize_projection(self):
        self.reject(('rust',), lambda r:r.update(state='failed'), 'actual complete parent Rust validation must pass')

    def test_borrowed_checkpoint(self):
        self.reject(('rust',), lambda r:r.update(head='borrowed'), 'exact independently built parent checkpoint')

    def test_changed_production(self):
        self.reject(('rust','production_inputs'), lambda r:r.update({'src/engine.rs':'changed'}), 'all44 unchanged tested Sena production inputs')

    def test_changed_source_during_run(self):
        self.reject(('rust',), lambda r:r.update(inputs_unchanged=False), 'all actual parent Rust inputs frozen')

    def test_missing_target(self):
        self.reject(('rust','all_targets'), lambda r:r.pop(), 'every262 parent Cargo target and all trailing checks')

    def test_failed_target(self):
        self.reject(('rust','results',1), lambda r:r.update(exit_code=1), 'every262 parent Cargo target and all trailing checks')

    def test_missing_doctest_command(self):
        self.reject(('rust','results',263,'command'), lambda r:r.__setitem__(-1,'--lib'), 'actual parent doctest Clippy inventory and diff checks')

    def test_current_ledger_cannot_be_refreshed(self):
        v = self.values.copy(); v['parent_raw'] += b' '
        with self.assertRaisesRegex(AssertionError, 'exact tested35764 parent ledger and test bytes'):
            audit.inspect(v, self.current, self.previous, self.production)

    def test_unknown_compiled_input(self):
        current = copy.deepcopy(self.current); current['klem']['src/extra.rs'] = 'changed'
        with self.assertRaisesRegex(AssertionError, 'every original1158/1158/18 profile member retained'):
            audit.inspect(self.values, current, self.previous, self.production)

    def test_nonparent_test_fixture_change(self):
        current = copy.deepcopy(self.current); current['klem']['tests/fixtures/friendly-hortative-sena-validity.json'] = 'changed'
        with self.assertRaisesRegex(AssertionError, 'only exact two tested Gena-parent input changes'):
            audit.inspect(self.values, current, self.previous, self.production)

    def test_borrowed_profile_bytes(self):
        current = copy.deepcopy(self.current); current['corpus-adapter']['tests/validity.rs'] = 'borrowed'
        with self.assertRaisesRegex(AssertionError, 'every current profile byte belongs to actual passed parent Rust source'):
            audit.inspect(self.values, current, self.previous, self.production)

    def test_rewritten_raw_log_rejected(self):
        v = self.values.copy(); v['rust_log'] += b'changed'
        with self.assertRaisesRegex(AssertionError, 'whole actual parent Rust log'):
            audit.inspect(v, self.current, self.previous, self.production)


if __name__ == '__main__': unittest.main()
