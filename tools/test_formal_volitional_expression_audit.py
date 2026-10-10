"""Reject lost expression identities, contexts, lexical targets and source tensions."""
import copy
import unittest

import formal_volitional_expression_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet, cls.suite = audit.inputs()

    def reject(self, mutate, reason):
        packet, suite = copy.deepcopy((self.packet, self.suite))
        mutate(packet, suite)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(packet, suite)

    def test_complete_original_sources(self):
        self.assertEqual(audit.inspect(self.packet, self.suite)['independent_targets'], 8)

    def test_missing_expression(self):
        self.reject(lambda p, s: p['expression_entries'].pop('krdict:89455'), 'separate expression identities')

    def test_homonym_must_remain_separate(self):
        self.reject(lambda p, s: p['expression_entries']['krdict:89456'].update(homonym='1'), 'expression homonym POS')

    def test_no_unclassified_ending_pos_fallback(self):
        self.reject(lambda p, s: p['expression_entries']['krdict:89455'].update(pos='어미'), 'expression homonym POS')

    def test_native_original_translation(self):
        self.reject(lambda p, s: p['complete_imported_entries']['krdict:89455']['senses'][0]['translations'].clear(), 'every complete original Native field')

    def test_original_dialogue_preserved(self):
        self.reject(lambda p, s: p['complete_groups'][2]['complete_original_group'].pop(), 'all complete original groups')

    def test_full_source_not_reconstructed_from_tokens(self):
        self.reject(lambda p, s: p.update(complete_source_text='가시렵니까'), 'all original source bytes')

    def test_source_cannot_borrow_ending_identity(self):
        self.reject(lambda p, s: s['sources'].update({'krdict:86548': s['sources']['krdict:89455']}), 'original expression source attribution')

    def test_vowel_stem_target_cannot_be_shortened(self):
        self.reject(lambda p, s: s['cases'][4]['judgments'][0].update(lemmas=['모다']), 'unchanged authored judgment')

    def test_no_automatic_contraction_expansion(self):
        self.reject(lambda p, s: s['cases'][0]['judgments'][0]['lemmas'].append('하다'), 'unchanged authored judgment')

    def test_source_tension_remains_visible(self):
        self.reject(lambda p, s: p['source_tensions'].clear(), 'original vowel stem source tension')


if __name__ == '__main__':
    unittest.main()
