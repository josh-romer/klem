import copy
import unittest
import formal_volitional_ledger_audit as audit


class LedgerProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual = audit.inputs()

    def altered(self):
        return copy.deepcopy(self.actual)

    def test_actual_independent_scopes_pass(self):
        self.assertEqual(audit.inspect(*self.actual)['ledger_cases'], 35587)

    def test_relabelled_original_judgment_is_rejected(self):
        values = self.altered()
        values[0]['cases'][0]['judgments'][0]['verdict'] = 'forbidden'
        with self.assertRaisesRegex(AssertionError, 'unchanged original judgments'):
            audit.inspect(*values)

    def test_raw_case_replacement_is_rejected_even_with_coordinated_ledger(self):
        values = self.altered()
        values[2]['cases'][0]['surface'] = 'invented'
        values[4]['cases'][35530] = copy.deepcopy(values[2]['cases'][0])
        with self.assertRaisesRegex(AssertionError, 'exact raw53'):
            audit.inspect(*values)

    def test_dictionary_case_cannot_replace_a_structural_case(self):
        values = self.altered()
        values[1]['dictionary_required_case_ids'][0] = values[2]['cases'][0]['id']
        with self.assertRaisesRegex(AssertionError, 'original six dictionary-POS cases'):
            audit.inspect(*values)

    def test_novel_case_rewrite_is_rejected_even_with_coordinated_ledger(self):
        values = self.altered()
        values[3]['cases'][0]['judgments'][0]['lemmas'] = ['invented다']
        values[4]['cases'][35583] = copy.deepcopy(values[3]['cases'][0])
        with self.assertRaisesRegex(AssertionError, 'unchanged manual novel judgments'):
            audit.inspect(*values)

    def test_original_source_link_cannot_change_in_projection(self):
        values = self.altered()
        values[2]['sources']['krdict:86549'] = 'https://example.invalid/changed'
        with self.assertRaisesRegex(AssertionError, 'original raw metadata'):
            audit.inspect(*values)


if __name__ == '__main__':
    unittest.main()
