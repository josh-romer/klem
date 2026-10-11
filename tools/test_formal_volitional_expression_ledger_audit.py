"""Reject parent rewrites, changed expressions and incomplete original Native fixtures."""
import copy
import unittest

import formal_volitional_expression_ledger_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.evidence)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_complete_original_append(self):
        self.assertEqual(audit.inspect(*self.evidence)['ledger_cases'], 35595)

    def test_parent_judgment_cannot_change(self):
        self.reject(lambda v: v[2]['cases'][0]['judgments'][0].update(reason='changed'), 'exact complete parent ledger bytes')

    def test_parent_source_cannot_change(self):
        self.reject(lambda v: v[2]['sources'].update({next(iter(v[2]['sources'])): 'https://example.invalid'}), 'exact complete parent ledger bytes')

    def test_expression_order_cannot_change(self):
        def mutate(v):
            v[2]['cases'][35587], v[2]['cases'][35588] = v[2]['cases'][35588], v[2]['cases'][35587]
        self.reject(mutate, 'exact eight appended judgments')

    def test_expression_source_cannot_borrow_an_ending(self):
        self.reject(lambda v: v[2]['sources'].update({'krdict:89455': v[2]['sources']['krdict:86548']}), 'separate expression source links')

    def test_original_native_fixture_cannot_drop_an_owner(self):
        self.reject(lambda v: v[3]['LexicalResource']['Lexicon']['LexicalEntry'].pop(), 'all exact original Native fixture fields')

    def test_importer_expectations_cannot_drop_translations(self):
        self.reject(lambda v: v[4]['krdict:89455']['senses'][0]['translations'].clear(), 'exact complete Rust importer expectations')

    def test_exact_complete_counts(self):
        self.reject(lambda v: v[5]['counts'].update(required=31344), 'complete independent ledger counts')


if __name__ == '__main__':
    unittest.main()
