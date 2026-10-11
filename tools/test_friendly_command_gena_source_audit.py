import copy
import unittest

import friendly_command_gena_source_audit as audit


class SourceAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = audit.inputs()

    def rejects(self, change):
        value = copy.deepcopy(self.original)
        change(value)
        with self.assertRaises((AssertionError, KeyError, ValueError, IndexError, StopIteration)):
            audit.inspect(value)

    def test_complete_scope_passes(self):
        result = audit.inspect(self.original)
        self.assertEqual((result['source_groups'], result['private_cases'], result['full_native_owners']), (4,24,31))

    def test_dialogue_group_cannot_be_trimmed(self):
        self.rejects(lambda v:v['source']['items'][3]['complete_original_group'].pop(0))

    def test_source_target_cannot_change_to_observed_competing_path(self):
        self.rejects(lambda v:v['source']['items'][0]['typed_target'].update(morphemes=['게','나']))

    def test_source_byte_span_is_preserved(self):
        self.rejects(lambda v:v['source']['items'][0]['local_span'].update(start=0))

    def test_pre_runtime_authoring_cannot_be_relabelled(self):
        self.rejects(lambda v:v['source'].update(candidate_runtime_observed=True))

    def test_original_native_definition_is_preserved(self):
        self.rejects(lambda v:v['entries']['krdict:66968']['senses'][0].update(definition='replacement'))

    def test_original_native_example_whitespace_is_preserved(self):
        self.rejects(lambda v:v['entries']['krdict:66968']['senses'][0]['examples'][0].append('extra'))

    def test_full_homonym_closure_cannot_be_reduced(self):
        self.rejects(lambda v:v['entries'].pop(next(k for k in v['entries'] if k!='krdict:66968')))

    def test_original_lmf_cannot_be_replaced_by_projection(self):
        self.rejects(lambda v:v['native']['LexicalResource']['Lexicon']['LexicalEntry'].pop())

    def test_ending_catalog_cannot_borrow_another_ending_owner(self):
        self.rejects(lambda v:v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'].append(v['native']['LexicalResource']['Lexicon']['LexicalEntry'][0]))

    def test_all_original_private_judgments_are_checked(self):
        self.rejects(lambda v:v['suite']['cases'].pop())

    def test_forbidden_judgment_cannot_be_weakened(self):
        self.rejects(lambda v:next(c for c in v['suite']['cases'] if c['judgments'][0]['verdict']=='forbidden')['judgments'][0].update(verdict='required'))

    def test_canonical_morphology_cannot_be_replaced_by_prior_reading(self):
        self.rejects(lambda v:v['suite']['cases'][0]['judgments'][0].update(morphemes=['게','나']))

    def test_existing_friendly_n_rule_cannot_substitute_for_gena(self):
        self.rejects(lambda v:v['suite']['cases'][0]['judgments'][0].update(required_rules=['ending.friendly_command.n']))

    def test_label_must_keep_own_source(self):
        self.rejects(lambda v:v['label']['sources'][0].update(id=73877))

    def test_label_must_keep_ending_kind(self):
        self.rejects(lambda v:v['label'].update(kind='particle'))

    def test_all_baseline_policies_are_retained(self):
        self.rejects(lambda v:v['captures']['captures'].pop())

    def test_baseline_full_frame_and_dictionary_assessment_bytes_are_retained(self):
        self.rejects(lambda v:v['captures']['captures'][0]['frames'][0].update(dictionary=None))

    def test_all_actual_native_responses_are_retained(self):
        self.rejects(lambda v:v['captures']['native_entries'].pop('krdict:66968'))

    def test_old_path_order_cannot_be_refreshed(self):
        self.rejects(lambda v:v['prior_paths'][0]['analysis']['analyses'].reverse())

    def test_every_old_word_record_is_checked(self):
        self.rejects(lambda v:v['prior_paths'].pop())

    def test_original_payload_hashes_cannot_be_refreshed(self):
        self.rejects(lambda v:v['originals'].update({'friendly-command-gena-validity.json':b'{}'}))


if __name__ == '__main__':
    unittest.main()
