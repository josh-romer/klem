import copy
import unittest

import friendly_hortative_sena_source_audit as audit


class SourceAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = audit.inputs()

    def rejects(self, change, field):
        value = dict(self.original)
        value[field] = copy.deepcopy(self.original[field])
        change(value)
        with self.assertRaises((AssertionError, KeyError, ValueError, IndexError, StopIteration)):
            audit.inspect(value)

    def test_complete_scope_passes(self):
        result = audit.inspect(self.original)
        self.assertEqual((result['source_groups'], result['private_cases'], result['full_native_owners'],
                          result['baseline_frames'], result['prior_word_records']), (5, 25, 36, 1608, 63))

    def test_original_dialogue_cannot_be_trimmed(self):
        self.rejects(lambda v: v['source']['items'][4]['complete_original_group'].pop(), field='source')

    def test_original_occurrence_span_cannot_change(self):
        self.rejects(lambda v: v['source']['items'][0]['local_span'].update(start=0), field='source')

    def test_source_target_cannot_follow_competing_runtime_reading(self):
        self.rejects(lambda v: v['source']['items'][0]['typed_target'].update(morphemes=['세', '나']), field='source')

    def test_rieul_source_target_cannot_be_replaced_by_homonym(self):
        self.rejects(lambda v: v['source']['items'][3]['typed_target'].update(lemmas=['사다']), field='source')

    def test_original_candidate_observation_state_is_retained(self):
        self.rejects(lambda v: v['source'].update(candidate_runtime_observed=True), field='source')

    def test_prior_historical_discovery_cannot_be_denied(self):
        self.rejects(lambda v: v['source'].update(historical_whole_inventory_discovery_already_exists=False), field='source')

    def test_independent_target_selection_cannot_be_relabelled(self):
        self.rejects(lambda v: v['source'].update(prior_discovery_outputs_used_for_target_selection=True), field='source')

    def test_metadata_correction_cannot_discard_original_producer(self):
        self.rejects(lambda v: v['source'].pop('original_authoring_producer'), field='source')

    def test_metadata_correction_cannot_claim_judgment_changes(self):
        self.rejects(lambda v: v['source']['metadata_label_correction'].update(case_and_judgment_bytes_unchanged=False), field='source')

    def test_related_ending_cannot_become_source_owner(self):
        self.rejects(lambda v: v['source']['owner_ids'].append('krdict:78404'), field='source')

    def test_independent_korean_review_cannot_be_claimed(self):
        self.rejects(lambda v: v['source']['items'][0].update(independent_korean_review='complete'), field='source')

    def test_every_preauthored_judgment_is_retained(self):
        self.rejects(lambda v: v['suite']['cases'].pop(), field='suite')

    def test_forbidden_irregular_recovery_cannot_be_weakened(self):
        self.rejects(lambda v: next(c for c in v['suite']['cases'] if c['judgments'][0]['verdict'] == 'forbidden')['judgments'][0].update(verdict='required'), field='suite')

    def test_canonical_path_cannot_be_replaced_by_se_plus_na(self):
        self.rejects(lambda v: v['suite']['cases'][0]['judgments'][0].update(morphemes=['세', '나']), field='suite')

    def test_rule_provenance_cannot_redefine_original_target(self):
        self.rejects(lambda v: v['suite']['cases'][0]['judgments'][0].update(required_rules=['ending.friendly_hortative.sena']), field='suite')

    def test_original_case_bytes_cannot_be_refreshed(self):
        self.rejects(lambda v: v.update(suite_raw=b'{}'), field='suite_raw')

    def test_all_native_homonyms_are_retained(self):
        self.rejects(lambda v: v['entries'].pop(next(k for k in v['entries'] if k != 'krdict:78469')), field='entries')

    def test_native_definition_is_retained(self):
        self.rejects(lambda v: v['entries']['krdict:78469']['senses'][0].update(definition='replacement'), field='entries')

    def test_native_translations_are_retained(self):
        self.rejects(lambda v: v['entries']['krdict:78469']['senses'][0]['translations'].pop(), field='entries')

    def test_original_native_example_whitespace_is_retained(self):
        self.rejects(lambda v: v['entries']['krdict:78469']['senses'][0]['examples'][0].append('extra'), field='entries')

    def test_original_full_lmf_is_retained(self):
        self.rejects(lambda v: v['native']['LexicalResource']['Lexicon']['LexicalEntry'].pop(), field='native')

    def test_catalog_cannot_borrow_related_ending(self):
        self.rejects(lambda v: v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'].append(v['native']['LexicalResource']['Lexicon']['LexicalEntry'][0]), field='ending_native')

    def test_label_cannot_borrow_se_owner(self):
        self.rejects(lambda v: v['label']['sources'][0].update(id=78404), field='label')

    def test_label_cannot_borrow_euse_owner(self):
        self.rejects(lambda v: v['label']['sources'][0].update(id=78434), field='label')

    def test_label_cannot_change_grammar_kind(self):
        self.rejects(lambda v: v['label'].update(kind='particle'), field='label')

    def test_actual_installed_baseline_revision_is_retained(self):
        self.rejects(lambda v: v['installed'].update(captured_head='different'), field='installed')

    def test_actual_installed_baseline_binary_is_retained(self):
        self.rejects(lambda v: v['installed']['binaries']['klem'].update(sha256='0' * 64), field='installed')

    def test_baseline_receipt_cannot_be_edited(self):
        self.rejects(lambda v: v['baseline'].update(required_lemma_role_matches=1), field='baseline')

    def test_baseline_receipt_cannot_drop_source_binding(self):
        self.rejects(lambda v: v['baseline']['source_inputs'].pop('src/grammar.rs'), field='baseline')

    def test_all_36_baseline_policies_are_retained(self):
        self.rejects(lambda v: v['captures']['captures'].pop(), field='captures')

    def test_baseline_cache_policy_is_retained(self):
        self.rejects(lambda v: v['captures']['captures'][0].update(cache_bytes=4096), field='captures')

    def test_baseline_full_input_is_retained(self):
        self.rejects(lambda v: v['captures']['captures'][0].update(input='하세나'), field='captures')

    def test_baseline_full_frames_and_assessments_are_retained(self):
        self.rejects(lambda v: v['captures']['captures'][0]['frames'][0].update(dictionary=None), field='captures')

    def test_baseline_canonical_match_cannot_be_invented(self):
        self.rejects(lambda v: v['captures']['captures'][0]['observations'][0].update(typed_path_present=True), field='captures')

    def test_baseline_lemma_match_cannot_be_invented(self):
        self.rejects(lambda v: v['captures']['captures'][0]['observations'][0].update(lemma_role_path_present=True), field='captures')

    def test_baseline_observation_cannot_be_omitted(self):
        self.rejects(lambda v: v['captures']['captures'][0]['observations'].pop(), field='captures')

    def test_all_native_cli_responses_are_retained(self):
        self.rejects(lambda v: v['captures']['native_entries'].pop('krdict:78469'), field='captures')

    def test_native_cli_stdout_is_retained(self):
        self.rejects(lambda v: v['captures']['native_entries']['krdict:78469'].update(stdout='{}'), field='captures')

    def test_every_prior_raw_word_is_retained(self):
        self.rejects(lambda v: v['prior_paths'].pop(), field='prior_paths')

    def test_prior_candidate_order_cannot_be_refreshed(self):
        def change(value):
            frame = next(f for f in value['prior_paths'] if len(f['analysis']['analyses']) > 1)
            frame['analysis']['analyses'].reverse()
        self.rejects(change, field='prior_paths')

    def test_original_payload_cannot_be_replaced(self):
        self.rejects(lambda v: v['originals'].update({f'{audit.PREFIX}-baseline.json': b'{}'}), field='originals')


if __name__ == '__main__':
    unittest.main()
