"""Corruption controls for whole Sena comparisons and original corpus attribution."""
import copy
import json
import unittest

import friendly_hortative_sena_wide_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = audit.inputs()

    def reject(self, check, path, change, reason):
        value = self.original.copy()
        node = value
        for key in path[:-1]:
            node[key] = copy.copy(node[key])
            node = node[key]
        node[path[-1]] = copy.deepcopy(node[path[-1]])
        change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError, reason):
            check(value)

    def test_whole_original_scope(self):
        result = audit.inspect(self.original)
        self.assertEqual((result['cohort_words'], result['annotated_rows'], result['broad_frames']), (53502, 66570, 1128312))
        self.assertFalse(result['full_coverage_complete'])

    def test_failed_receipt_cannot_be_relabelled(self):
        self.reject(audit.inspect_receipts, ('wide',), lambda r:r.update(state='failed'), 'actual passed terminal')

    def test_source_snapshot_cannot_omit_old_assertions(self):
        self.reject(audit.inspect_receipts, ('wide','frozen_inputs'), lambda r:r.pop('tests/friendly_command_gena.rs'), 'whole7067')

    def test_complete_collector_command_cannot_be_omitted(self):
        self.reject(audit.inspect_receipts, ('wide','results'), lambda r:r.pop(), 'all three actual')

    def test_actual_whole_log_cannot_change(self):
        self.reject(audit.inspect_receipts, ('wide',), lambda r:r.update(log_sha256='changed'), 'whole original wide log')

    def test_missing_original_outcome_cannot_become_passed(self):
        self.reject(audit.inspect_receipts, ('stopped',), lambda r:r.update(exit_code=0), 'unknown original outcome')

    def test_current_binary_binding_cannot_change(self):
        binary = self.original['runtime']['binding']['binaries']['klem']['path']
        self.reject(audit.inspect_cohorts, ('cohorts','frozen_inputs'), lambda r:r.update({binary:'changed'}), 'exact Source-bound')

    def test_capture_production_input_cannot_change(self):
        key='/home/josh/projects/klem/.direnv/friendly-hortative-sena/src/dictionary/proper_names.json'
        self.reject(audit.inspect_broad, ('broad','frozen_inputs'), lambda r:r.update({key:'changed'}), 'all44 capture')

    def test_historical_word_cannot_be_dropped(self):
        self.reject(audit.inspect_cohorts, ('cohorts','runs',1,'captures',1,'words'), lambda r:r.pop(next(iter(r))), 'whole word set')

    def test_original_candidate_cannot_be_removed(self):
        self.reject(audit.inspect_cohorts, ('cohorts','runs',0,'captures',1,'words','중세나','analyses'), lambda r:r.pop(1), 'every old candidate and relative order')

    def test_original_candidate_order_cannot_change(self):
        self.reject(audit.inspect_cohorts, ('cohorts','runs',0,'captures',1,'words','중세나','analyses'), lambda r:r.reverse(), 'every old candidate and relative order')

    def test_canonical_path_cannot_borrow_se_plus_na(self):
        def change(paths):
            paths[0]['morphemes']=[dict(form='세',kind='ending'),dict(form='나',kind='particle')]
        self.reject(audit.inspect_cohorts, ('cohorts','runs',0,'captures',1,'words','중세나','analyses'), change, 'only canonical Sena additions')

    def test_changed_case_cannot_be_omitted(self):
        self.reject(audit.inspect_cohorts, ('cohorts','individual_changed_words'), lambda r:r.clear(), 'complete individual word records')

    def test_post_runtime_hypothesis_cannot_become_reviewed(self):
        self.reject(audit.inspect_cohorts, ('cohorts','individual_changed_words',0), lambda r:r.update(contextual_verdict='required'), 'complete individual word records')

    def test_annotated_partition_cannot_be_omitted(self):
        self.reject(audit.inspect_gold, ('gold','runs'), lambda r:r.pop(), 'all66570')

    def test_annotated_row_cannot_change_even_with_refreshed_stdout(self):
        def change(run):
            rows=[json.loads(line) for line in run['jsonl'].splitlines()]
            rows[1]['expected']=['changed']
            run['jsonl']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
            run['stdout_sha256']=audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_gold, ('gold','runs',0), change, 'every full original gold row')

    def test_gold_recovery_cannot_change_even_with_refreshed_stdout(self):
        def change(run):
            rows=[json.loads(line) for line in run['jsonl'].splitlines()]
            rows[1]['recovered_sets']=[[123]]
            run['jsonl']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
            run['stdout_sha256']=audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_gold, ('gold','runs',0), change, 'every full original gold row')

    def test_gold_summary_delta_cannot_be_hidden(self):
        self.reject(audit.inspect_gold, ('gold','runs',1,'summary_changes'), lambda r:r.clear(), 'all gold summary changes')

    def test_broad_mode_cannot_be_dropped(self):
        self.reject(audit.inspect_broad, ('broad','runs'), lambda r:r.pop(), 'all1128312')

    def test_novel_output_fingerprint_cannot_change(self):
        self.reject(audit.inspect_broad, ('broad','runs',3), lambda r:r.update(after_jsonl_sha256='changed'), 'every full original output byte')

    def test_spacing_filter_command_cannot_change(self):
        self.reject(audit.inspect_broad, ('broad','runs',7,'commands',1), lambda r:r.pop(), 'actual full filter')

    def test_old_path_occurrences_cannot_be_underreported(self):
        self.reject(audit.inspect_broad, ('broad','runs',0), lambda r:r.update(original_paths_preserved=0), 'all original candidate occurrences')

    def test_new_broad_path_cannot_be_ignored(self):
        self.reject(audit.inspect_broad, ('broad','runs',0), lambda r:r.update(new_family_paths=1), 'zero broad candidate')

    def test_corpus_observation_cannot_invent_historical_allowance(self):
        self.reject(audit.inspect_observation, ('history',), lambda r:r.update(historical_allowances_assigned=True), 'zero historical witnesses')

    def test_original_token_annotation_cannot_change(self):
        self.reject(audit.inspect_observation, ('observation','items',0,'complete_original_token_fields'), lambda r:r.__setitem__(2,'중다+세나'), 'all original token fields')

    def test_original_sentence_cannot_be_truncated(self):
        self.reject(audit.inspect_observation, ('observation','items',0), lambda r:r.update(complete_original_conllu_block='중세나'), 'complete original sentence')

    def test_source_gold_case_cannot_be_relabelled(self):
        self.reject(audit.inspect_observation, ('observation','items',0,'original_gold_row'), lambda r:r.update(expected=['중다']), 'exact unchanged original gold row')

    def test_unmatched_candidate_head_cannot_be_omitted(self):
        self.reject(audit.inspect_native, ('native','selected_heads'), lambda r:r.remove('중다'), 'every actual new candidate head')

    def test_same_head_native_owner_cannot_be_removed(self):
        self.reject(audit.inspect_native, ('native','complete_native_entries'), lambda r:r.pop(next(iter(r))), 'all41 complete Native')

    def test_full_native_sense_cannot_be_removed(self):
        self.reject(audit.inspect_native, ('native','complete_native_entries'), lambda r:next(e for e in r.values() if e['senses'])['senses'].pop(), 'all41 complete Native')

    def test_original_export_cannot_be_refreshed(self):
        self.reject(audit.inspect_native, ('native','source_exports'), lambda r:r.pop(next(iter(r))), 'same11 complete original')

    def test_dictionary_fingerprint_cannot_change(self):
        def change(query):
            value=json.loads(query['stdout']);value['fingerprint']='changed';query['stdout']=json.dumps(value)
        self.reject(audit.inspect_native, ('native','actual_headword_queries','중다'), change, 'original dictionary identity')

    def test_unmatched_lemma_cannot_acquire_invented_dictionary_owner(self):
        def change(query):
            value=json.loads(query['stdout']);value['entries']=[dict(id='invented',headword='중다',homonym=None,pos='동사')];query['stdout']=json.dumps(value)
        self.reject(audit.inspect_native, ('native','actual_headword_queries','중다'), change, 'every same-head Native')

    def test_native_context_cannot_be_certified(self):
        self.reject(audit.inspect_native, ('native',), lambda r:r.update(contextual_verdict='required'), 'Native attribution is not contextual')


if __name__=='__main__':
    unittest.main()
