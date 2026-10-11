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

    def test_unreviewed_tail_cannot_hide_behind_historical_prefix(self):
        values = self.altered()
        values[4]['cases'].append(copy.deepcopy(values[4]['cases'][-1]))
        with self.assertRaisesRegex(AssertionError, 'complete append-only ledger'):
            audit.inspect(*values)

    def test_reviewed_tail_judgment_cannot_change(self):
        values = self.altered()
        self.assertGreater(len(values[4]['cases']), 35587)
        values[4]['cases'][-1]['judgments'][0]['verdict'] = 'invented'
        with self.assertRaisesRegex(AssertionError, 'complete append-only ledger'):
            audit.inspect(*values)

    def test_reviewed_tail_order_cannot_change(self):
        values = self.altered()
        cases = values[4]['cases']
        cases[-2], cases[-1] = cases[-1], cases[-2]
        with self.assertRaisesRegex(AssertionError, 'complete append-only ledger'):
            audit.inspect(*values)

    def test_reviewed_tail_case_cannot_be_omitted(self):
        values = self.altered()
        values[4]['cases'].pop()
        with self.assertRaisesRegex(AssertionError, 'complete append-only ledger'):
            audit.inspect(*values)

    def test_reviewed_tail_source_cannot_change(self):
        values = self.altered()
        source = next(iter(audit.read('formal-volitional-expression-validity.json')['sources']))
        values[4]['sources'][source] = 'https://example.invalid/changed'
        with self.assertRaisesRegex(AssertionError, 'complete append-only ledger'):
            audit.inspect(*values)


if __name__ == '__main__':
    unittest.main()
