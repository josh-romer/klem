"""Require complete actual promotion before exposing historical parent evidence."""
import unittest

import friendly_hortative_sena_gena_parent_audit as parent
import friendly_hortative_sena_revision as revision
import friendly_hortative_sena_promotion_audit as promotion


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.revision = revision.inputs()
        cls.values = cls.revision['verified_parent_update']
        cls.current = cls.revision['actual_current_profiles']
        cls.previous = {name: row['files'] for name, row in cls.revision['selected']['friendly-hortative-sena-wide-selected-source.json']['profiles'].items()}
        cls.production = cls.revision['browser']['runtime']['binding']['production_inputs']

    def inspect(self, value):
        return parent.inspect(value, self.current, self.previous, self.production)

    def test_current_and_historical_counts_are_explicit(self):
        report = self.inspect(self.values)
        self.assertEqual((report['parent_cases'], report['parent_reviews'], report['full_rust_tests']), (35764, 520, 1212))
        self.assertEqual((report['verified_current_shared_cases'], report['verified_current_shared_reviews'], report['verified_current_full_rust_tests']), (35789, 521, 1213))
        self.assertTrue(report['actual_current25_Sena_cases_promoted'])
        self.assertFalse(report['full_coverage_complete'])

    def test_child_cannot_be_removed(self):
        value = dict(self.values); value.pop('verified_promotion')
        with self.assertRaises(KeyError): self.inspect(value)

    def test_complete_actual_ledger_binding_cannot_be_removed(self):
        value = dict(self.values); value.pop('actual_parent_raw')
        with self.assertRaises(KeyError): self.inspect(value)

    def test_complete_actual_test_binding_cannot_be_removed(self):
        value = dict(self.values); value.pop('actual_parent_test_raw')
        with self.assertRaises(KeyError): self.inspect(value)

    def test_complete_actual_ledger_binding_cannot_be_truncated(self):
        value = dict(self.values, actual_parent_raw=self.values['parent_raw'])
        with self.assertRaisesRegex(AssertionError, 'mandatory complete actual promoted ledger'): self.inspect(value)

    def test_complete_actual_test_binding_cannot_be_borrowed(self):
        value = dict(self.values, actual_parent_test_raw=self.values['parent_test_raw'])
        with self.assertRaisesRegex(AssertionError, 'mandatory complete actual promoted test bytes'): self.inspect(value)

    def test_historical_view_cannot_replace_actual_profiles(self):
        with self.assertRaisesRegex(AssertionError, 'every current profile byte belongs to actual passed parent Rust source'):
            historical = promotion.parent_profiles(self.values['verified_promotion'], self.current)
            parent.inspect(self.values, historical, self.previous, self.production)

    def test_child_current_profiles_cannot_be_rewritten(self):
        value = dict(self.values); value['verified_promotion'] = dict(value['verified_promotion'])
        profiles = dict(value['verified_promotion']['current_profiles']); profiles['klem'] = dict(profiles['klem'])
        profiles['klem']['tests/validity.rs'] = 'borrowed'
        value['verified_promotion']['current_profiles'] = profiles
        with self.assertRaisesRegex(AssertionError, 'every actual selected tested promotion profile byte'): self.inspect(value)

    def test_revision_cannot_drop_parent_after_projection(self):
        value = dict(self.revision, verified_parent_update=None)
        with self.assertRaisesRegex(AssertionError, 'mandatory complete promoted parent proof'): revision.inspect(value)

    def test_revision_cannot_supply_historical_profiles_as_actual(self):
        value = dict(self.revision, actual_current_profiles=self.revision['current_profiles'])
        with self.assertRaisesRegex(AssertionError, 'complete actual promoted profiles'): revision.inspect(value)


if __name__ == '__main__':
    unittest.main()
