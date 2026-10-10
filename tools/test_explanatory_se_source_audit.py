"""Reject changed source fields and coordinated changes to authored targets."""
import copy
import unittest

import explanatory_se_source_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, mutation, reason):
        values = copy.deepcopy(self.evidence)
        mutation(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_all_original_groups_and_correction(self):
        result = audit.inspect(*self.evidence)
        self.assertEqual(result['complete_groups'], 21)
        self.assertTrue(result['canonical_correction_preserved'])

    def test_native_original_unknown_field(self):
        self.reject(lambda v: v[0]['original_native_entries']['krdict:79278'].update(invented=True), 'pinned initial Native fields')

    def test_authored_original_unknown_field(self):
        def change(v):
            v[3]['LexicalResource']['Lexicon']['LexicalEntry'][0]['invented'] = True
            v[2]['original_native_entries'][audit.entry(v[3]['LexicalResource']['Lexicon']['LexicalEntry'][0])['id']]['invented'] = True
        self.reject(change, 'pinned authored Native fields')

    def test_short_full_notes_not_merged(self):
        self.reject(lambda v: v[0]['expression_entries']['krdict:79278'].update(notes=v[0]['expression_entries']['krdict:79279']['notes']), 'original separate attachment notes')

    def test_missing_complete_group(self):
        self.reject(lambda v: v[0]['complete_groups'].pop(), 'every complete original group')

    def test_original_trailing_spaces(self):
        self.reject(lambda v: v[0].update(complete_source_text=v[0]['complete_source_text'] + ' '), 'complete source bytes')

    def test_missing_prechange_filter(self):
        self.reject(lambda v: v[1]['proposals'][0]['baseline_records'].pop('compatible'), 'complete original baseline filters')

    def test_target_original_byte_location(self):
        self.reject(lambda v: v[1]['proposals'][0].update(surface_byte_offset=0), 'original target byte location')

    def test_original_judgment_lemma(self):
        self.reject(lambda v: v[5]['cases'][0]['judgments'][0].update(lemmas=['fabricated']), 'original authored target identity')

    def test_corrected_case_cannot_change_surface(self):
        def change(v):
            next(c for c in v[5]['cases'] if c['id'] == v[7]['case_id'])['surface'] = 'fabricated'
        self.reject(change, 'only source-based canonical naming corrected')

    def test_original_typo_retained(self):
        self.reject(lambda v: v[7].update(original_morphemes=['오', '그려']), 'retained original canonical typo')

    def test_correction_original_note(self):
        self.reject(lambda v: v[7].update(complete_original_source_notes=[]), 'correction original source note')

    def test_correction_initial_suite_binding(self):
        self.reject(lambda v: v[7].update(original_suite_sha256='0' * 64), 'immutable original authored suite binding')

    def test_particle_label_key(self):
        def change(v):
            v[8]['-그려'] = copy.deepcopy(v[8]['그려'])
        self.reject(change, 'particle key separate from ending keys')

    def test_particle_label_source(self):
        self.reject(lambda v: v[8]['그려']['sources'][0].update(id=79278), 'actual component key and Source label identities')


if __name__ == '__main__':
    unittest.main()
