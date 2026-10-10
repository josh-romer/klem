"""Reject altered source owners, authored targets and baseline provenance."""
import copy
import unittest

import formal_volitional_source_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.evidence)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_complete_source_packet(self):
        self.assertEqual(audit.inspect(*self.evidence)['source_groups'], 17)

    def test_original_note(self):
        self.reject(lambda v: v[0]['expression_entries']['krdict:86548']['notes'].clear(), 'expression identity|attachment note')

    def test_merged_source_owner(self):
        self.reject(lambda v: v[0]['expression_entries'].pop('krdict:86605'), 'separate ending owners')

    def test_complete_group(self):
        self.reject(lambda v: v[0]['complete_groups'].pop(), 'complete original source group')

    def test_complete_text(self):
        self.reject(lambda v: v[0].update(complete_source_text='changed'), 'original source bytes')

    def test_authored_timing(self):
        self.reject(lambda v: v[1].update(state='observed-after-engine-output'), 'proposal timing')

    def test_source_binding(self):
        self.reject(lambda v: v[1].update(source_preparation_sha256='0'*64), 'source binding')

    def test_original_byte_span(self):
        def change(v):
            v[0]['independent_proposals'][0]['surface_byte_offset'] += 1
            v[1]['proposals'][0]['surface_byte_offset'] += 1
        self.reject(change, 'original byte span')

    def test_canonical_target(self):
        self.reject(lambda v: v[4]['cases'][0]['judgments'][0].update(morphemes=['렵니다']), 'canonical target')

    def test_lexical_target(self):
        self.reject(lambda v: v[4]['cases'][0]['judgments'][0].update(lemmas=['보이다']), 'canonical target')

    def test_required_verdict(self):
        self.reject(lambda v: v[4]['cases'][0]['judgments'][0].update(verdict='forbidden'), 'forbidden boundaries')

    def test_typed_lemma_role(self):
        self.reject(lambda v: v[4]['cases'][0]['judgments'][0].update(lemma_kinds=['nominal']), 'canonical target')

    def test_individual_source(self):
        self.reject(lambda v: v[4]['cases'][0]['judgments'][0].update(source='krdict:86604'), 'judgment source ownership')

    def test_unrelated_boundary_correction(self):
        self.reject(lambda v: v[4]['cases'][-1]['judgments'][0].update(reason='rewritten after observation'), 'immutable independently authored judgments')

    def test_missing_native_owner(self):
        self.reject(lambda v: v[6].pop(next(iter(v[6]))), 'complete authored Native owners')

    def test_original_native_field(self):
        self.reject(lambda v: v[5]['LexicalResource']['Lexicon']['LexicalEntry'][0].update(invented=True), 'original authored Native fields')

    def test_native_projection(self):
        self.reject(lambda v: v[6][next(iter(v[6]))].update(pos='invented'), 'complete authored Native owners')

    def test_baseline_mode(self):
        self.reject(lambda v: v[7]['runs'].pop(), '102 original baseline')

    def test_baseline_command(self):
        self.reject(lambda v: v[7]['runs'][0]['command'].append('--dict-only'), 'filter command')

    def test_baseline_success(self):
        self.reject(lambda v: v[7]['runs'][0].update(exit_code=1), 'successful original baseline')

    def test_label_source(self):
        self.reject(lambda v: v[8]['-으렵니까']['sources'][0].update(id=77346), 'label ending owners')

    def test_source_sense_label(self):
        self.reject(lambda v: v[8]['-으렵니까'].update(label='Intention statement'), 'question and statement labels')

    def test_label_native_owner(self):
        self.reject(lambda v: v[9]['LexicalResource']['Lexicon']['LexicalEntry'].pop(), 'label source fields')


    def test_policy_timing(self):
        self.reject(lambda v: v[10].update(state='observed-after-prototype'), 'policy timing')

    def test_policy_suite_binding(self):
        self.reject(lambda v: v[10].update(authored_suite_sha256='0'*64), 'policy judgment binding')

    def test_dropped_dictionary_judgment(self):
        self.reject(lambda v: v[10]['dictionary_required_case_ids'].pop(), 'dictionary POS judgments')

    def test_dictionary_scope_reduced(self):
        self.reject(lambda v: v[10].update(dictionary_cases=53), 'raw and dictionary evaluation scopes')

    def test_baseline_record_rewritten(self):
        self.reject(lambda v: v[7]['runs'][0].update(stdout_sha256='0'*64), 'immutable complete baseline')

    def test_spoken_note_removed(self):
        self.reject(lambda v: v[0]['expression_entries']['krdict:86549']['senses'][0]['notes'].clear(), 'expression identity|preparation fields')

    def test_coordinated_added_native_rewrite(self):
        def change(v):
            initial = set(v[0]['original_native_entries'])
            lexical = next(value for value in v[5]['LexicalResource']['Lexicon']['LexicalEntry'] if audit.entry(value)['id'] not in initial)
            lexical['invented'] = 'coordinated'
            v[3]['original_native_entries'][audit.entry(lexical)['id']] = copy.deepcopy(lexical)
        self.reject(change, 'immutable authored Native closure')


if __name__ == '__main__':
    unittest.main()
