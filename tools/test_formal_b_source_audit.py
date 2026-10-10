"""Reject lost source groups, changed roles and weakened individual requirements."""
import copy
import unittest
import formal_b_source_audit as audit


class SourceGuards(unittest.TestCase):
    def setUp(self):
        self.values = copy.deepcopy(audit.inputs())

    def rejects(self):
        with self.assertRaises(AssertionError):
            audit.inspect(*self.values)

    def test_complete_original_source_scope(self):
        self.assertEqual(audit.inspect(*self.values)['native_entries'], 92)

    def test_lost_original_group(self):
        self.values[0]['complete_groups'].pop()
        self.rejects()

    def test_lost_native_homonym(self):
        self.values[2]['LexicalResource']['Lexicon']['LexicalEntry'].pop()
        self.rejects()

    def test_changed_original_ending_role(self):
        self.values[0]['complete_imported_entries']['krdict:80528']['pos'] = '명사'
        self.rejects()

    def test_shortened_proposal_context(self):
        self.values[3][0]['complete_original_group'] = ['큽디다']
        self.rejects()

    def test_weakened_source_judgment(self):
        self.values[4]['cases'][0]['judgments'][0]['required_rules'] = []
        self.rejects()

    def test_lost_boundary_case(self):
        self.values[4]['cases'].pop()
        self.rejects()

    def test_merged_allomorph_source_identities(self):
        self.values[5]['-습디다']['sources'].pop()
        self.rejects()

    def test_missing_complete_label_owner(self):
        self.values[6]['LexicalResource']['Lexicon']['LexicalEntry'].pop()
        self.rejects()


if __name__ == '__main__':
    unittest.main()
