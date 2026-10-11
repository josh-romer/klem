"""Reject changed independent targets, Native owners and original observations."""
import copy
import gzip
import json
import unittest

import gentle_command_long_source_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.values)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(values)

    def test_complete_independent_scope(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['cases'], result['required'], result['native_owners']), (25, 16, 43))
        self.assertFalse(result['full_coverage_complete'])

    def test_original_payload_cannot_be_reauthored(self):
        self.reject(lambda v: v['originals'].update({'gentle-command-long-original-source.json': b'{}'}),
                    'all original source payload bytes')

    def test_original_source_group_cannot_be_cropped(self):
        def mutate(v):
            source = json.loads(v['source_raw'])
            source['items'][0]['complete_original_group'] = ['자려무나']
            v['source_raw'] = (json.dumps(source, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'complete original source fixture')

    def test_private_forbidden_cannot_be_promoted(self):
        self.reject(lambda v: v['suite']['cases'][15]['judgments'][0].update(verdict='required'),
                    'every original private judgment field')

    def test_coordinated_private_judgment_rewrite_is_rejected(self):
        def mutate(v):
            v['suite']['cases'][0]['judgments'][0]['lemmas'] = ['invented']
            v['suite_raw'] = (json.dumps(v['suite'], ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'exact independently authored25 judgments')

    def test_original_native_attachment_note_cannot_expand(self):
        self.reject(lambda v: v['entries']['krdict:79266'].update(notes=['all predicates']),
                    'every original imported source field/homonym')

    def test_original_existential_homonym_cannot_disappear(self):
        self.reject(lambda v: v['entries'].pop('krdict:68797'), 'every original imported source field/homonym')

    def test_full_native_source_cannot_be_shortened(self):
        self.reject(lambda v: v['native']['LexicalResource']['Lexicon']['LexicalEntry'].pop(),
                    'every original source Native field/order')

    def test_boundary_homonym_cannot_disappear(self):
        self.reject(lambda v: v['boundary_entries'].pop('krdict:38524'), 'every inherited boundary field/homonym')

    def test_boundary_native_order_cannot_change(self):
        self.reject(lambda v: v['boundary_native']['LexicalResource']['Lexicon']['LexicalEntry'].reverse(),
                    'all27 original boundary Native fields/order')

    def test_catalog_fixture_cannot_drop_long_owner(self):
        self.reject(lambda v: v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'].pop(),
                    'catalog fixture has both exact ending owners')

    def test_label_cannot_borrow_short_owner(self):
        self.reject(lambda v: v['label']['sources'][0].update(id=79340), 'label owns only the two original long endings')

    def test_prior_baseline_cannot_drop_policy(self):
        self.reject(lambda v: v['baseline']['runs'].pop(), 'unchanged actual prior baseline observations')

    def test_coordinated_baseline_refresh_is_rejected(self):
        def mutate(v):
            v['baseline']['runs'][0]['observations'][0]['lexical_path_indices'] = [0]
            v['baseline_raw'] = gzip.compress((json.dumps(v['baseline'], ensure_ascii=False, indent=2) + '\n').encode(), mtime=0)
        self.reject(mutate, 'exact original baseline payload bytes')

    def test_previous_word_analysis_cannot_be_cropped(self):
        self.reject(lambda v: v['prior_paths'][0]['actual_record']['analysis']['analyses'].pop(),
                    'all8 full original baseline records retained')

    def test_additional_derived_class_judgments_cannot_be_refreshed(self):
        self.reject(lambda v: v.update(interactions_raw=b'{}'), 'exact additional derived-class judgments')

    def test_derived_suffix_cannot_become_a_second_lexical_lemma(self):
        self.reject(lambda v: v['interactions']['cases'][0]['judgments'][0].update(lemmas=['학생', '답다']),
                    'actual nominal-plus-suffix target fields')

    def test_novel_context_packet_cannot_be_refreshed(self):
        self.reject(lambda v: v.update(novel_packet_raw=b'{}'), 'exact original novel occurrence packet')

    def test_novel_proposal_cannot_be_reauthored(self):
        self.reject(lambda v: v.update(novel_suite_raw=b'{}'), 'exact eight bounded novel proposals')

    def test_novel_lexical_homonym_cannot_disappear(self):
        self.reject(lambda v: v['novel_entries'].pop(next(iter(v['novel_entries']))),
                    'all fifteen complete novel Native owners')


if __name__ == '__main__':
    unittest.main()
