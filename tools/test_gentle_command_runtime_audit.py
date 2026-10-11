"""Reject incomplete or rewritten runtime evidence, including refreshed hashes."""
import copy
import json
import unittest

import gentle_command_runtime_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self, check, path, mutate, reason):
        # Copy only the selected branch, retaining the complete original corpus
        # elsewhere. Each test changes one property of real captured evidence.
        values = self.values.copy()
        node = values
        for key in path[:-1]:
            node[key] = copy.copy(node[key])
            node = node[key]
        node[path[-1]] = copy.deepcopy(node[path[-1]])
        mutate(node[path[-1]])
        with self.assertRaisesRegex(AssertionError, reason):
            check(values)

    def test_complete_original_capture(self):
        result = audit.inspect(self.values)
        self.assertEqual(result['changed_annotated_rows'], 0)
        self.assertFalse(result['full_coverage_complete'])

    def test_full_suite_cannot_be_failed(self):
        self.reject(audit.inspect_bindings, ('full',), lambda r: r.update(state='failed'), 'terminal unchanged')

    def test_suite_cannot_hide_a_failure(self):
        self.reject(audit.inspect_bindings, ('full', 'totals'), lambda r: r.update(failed=1), 'complete actual Rust suite')

    def test_source_freeze_cannot_be_missing(self):
        self.reject(audit.inspect_bindings, ('full',), lambda r: r.update(head_unchanged=False), 'complete frozen source')

    def test_compiled_data_cannot_be_omitted(self):
        self.reject(audit.inspect_bindings, ('closure', 'production_inputs'), lambda r: r.pop(next(k for k in r if k.endswith('proper_names.json'))), 'complete production closure')

    def test_current_production_cannot_differ(self):
        self.reject(audit.inspect_bindings, ('current_production',), lambda r: r.update({next(iter(r)): 'changed'}), 'current complete production closure')

    def test_unrecorded_ending_revision_cannot_replace_captured_long_revision(self):
        self.reject(audit.inspect_bindings, ('current_production',), lambda r: r.update({'/tmp/klem-gentle-command/src/grammar.rs': 'unrecorded'}), 'current complete production closure')

    def test_binary_identity_cannot_be_replaced(self):
        self.reject(audit.inspect_bindings, ('closure', 'binaries'), lambda r: r['klem'].update(sha256='changed'), 'exact actual executable identity')

    def test_running_binding_cannot_claim_terminal_proof(self):
        self.reject(audit.inspect_bindings, ('binding',), lambda r: r.update(observed_full_rust_state='passed'), 'original in-progress production binding')

    def test_source_policy_cannot_disappear(self):
        self.reject(audit.inspect_streams, ('streams', 'runs'), lambda r: r.pop(), 'all36source policies')

    def test_source_filter_command_cannot_change(self):
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), lambda r: r['command'].append('--dict-only'), 'actual source filter/cache command')

    def test_dialogue_cannot_be_cropped(self):
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), lambda r: r.update(input_text='오렴'), 'complete original source bytes')

    def test_source_byte_span_cannot_shift_even_with_refreshed_hash(self):
        def shift(run):
            rows = [json.loads(line) for line in run['jsonl'].splitlines()]
            rows[0]['span']['start'] += 1
            run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows)
            run['jsonl_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), shift, 'contiguous original source spans')

    def test_individual_observation_cannot_borrow_another_record(self):
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), lambda r: r['observations'][0].update(record_index=0), 'all468individuallyrederivedobservations')

    def test_private_judgments_cannot_be_silently_promoted(self):
        self.reject(audit.inspect_streams, ('streams',), lambda r: r.update(linguistic_judgments_promoted=True), 'private judgments not silently promoted')

    def test_native_owner_cannot_disappear(self):
        self.reject(audit.inspect_native, ('native', 'records'), lambda r: r.pop(), 'all47completeNativeowners')

    def test_native_complete_notes_cannot_be_rewritten(self):
        self.reject(audit.inspect_native, ('native', 'records', 0), lambda r: r['complete_original_entry'].update(notes=[]), 'all original Native fields')

    def test_native_command_cannot_query_other_owner(self):
        self.reject(audit.inspect_native, ('native', 'records', 0), lambda r: r['captures'][0]['command'].__setitem__(-1, 'krdict:76564'), 'actual bound Native CLI and owner')

    def test_probe_cannot_be_claimed_as_original_annotations(self):
        self.reject(audit.inspect_gold, ('adapter',), lambda r: r.update(synthetic_probe_is_annotated_corpus=True), 'synthetic source probe kept separate')

    def test_probe_proposal_cannot_be_changed(self):
        self.reject(audit.inspect_gold, ('adapter', 'independently_authored_proposals'), lambda r: r[0].update(expected=['invented']), 'unchanged independently authored lexical proposals')

    def test_probe_row_cannot_change_with_refreshed_checksum(self):
        def rewrite(capture):
            rows = [json.loads(line) for line in capture['jsonl'].splitlines()]
            rows[1]['expected'] = ['invented']
            capture['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows)
            capture['stdout_sha256'] = audit.sha(capture['jsonl'].encode())
        self.reject(audit.inspect_gold, ('adapter', 'captures', 1), rewrite, 'every independently authored probe row')

    def test_corpus_partition_cannot_disappear(self):
        self.reject(audit.inspect_gold, ('gold', 'runs'), lambda r: r.pop(), 'all four original partitions')

    def test_corpus_adapter_cannot_be_replaced(self):
        self.reject(audit.inspect_gold, ('gold', 'runs', 0), lambda r: r['command'].__setitem__(0, '/wrong/adapter'), 'actual bound adapters')

    def test_original_gold_cannot_change_with_refreshed_checksum(self):
        def rewrite(run):
            rows = [json.loads(line) for line in run['jsonl'].splitlines()]
            rows[1]['expected'] = ['invented']
            run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows)
            run['stdout_sha256'] = audit.sha(run['jsonl'].encode())
            run['before_stdout_sha256'] = run['stdout_sha256']
        self.reject(audit.inspect_gold, ('gold', 'runs', 0), rewrite, 'every original annotated output byte unchanged')

    def test_gold_summary_cannot_hide_a_delta(self):
        self.reject(audit.inspect_gold, ('gold', 'runs', 0), lambda r: r.update(summary_changes={'lemma_recall': 1}), 'unchanged original corpus summaries')

    def test_broad_filter_policy_cannot_disappear(self):
        self.reject(audit.inspect_broad, ('broad', 'runs'), lambda r: r.pop(), 'all eight complete broad streams')

    def test_broad_cannot_claim_the_wrong_binary(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 0), lambda r: r['commands'][1].__setitem__(0, '/wrong/klem'), 'both actual bound broad binaries')

    def test_broad_spacing_cannot_be_omitted(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 6), lambda r: r['commands'][1].pop(), 'actual broad filter/spacing command')

    def test_novel_context_cannot_be_cropped(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 3), lambda r: r['changed_frames'][0].update(complete_original_line='주렴'), 'complete original novel context')

    def test_old_novel_candidate_order_cannot_change(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 3), lambda r: r['changed_frames'][0]['after']['analysis']['analyses'].reverse(), 'every original candidate and order')

    def test_old_native_assessment_cannot_change(self):
        def rewrite(run):
            change = run['changed_frames'][0]
            old_path = change['before']['analysis']['analyses'][0]
            index = change['after']['analysis']['analyses'].index(old_path)
            change['after']['dictionary']['readings'][index]['status'] = 'incompatible'
        self.reject(audit.inspect_broad, ('broad', 'runs', 3), rewrite, 'every original Native assessment')

    def test_novel_added_path_cannot_be_declared_correct(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 3), lambda r: r['changed_frames'][0].update(contextual_verdict='required'), 'individual novel hypothesis remains unjudged')

    def test_contextual_inference_cannot_claim_independent_review(self):
        self.reject(audit.inspect_context, ('context',), lambda r: r.update(independent_review='complete'), 'bounded contextual inference scope')

    def test_rare_noun_cannot_be_invented_in_dictionary(self):
        def rewrite(review):
            lookup = review['missing_krdict_lookup']
            value = json.loads(lookup['json']); value['entries'] = [{'headword': '주렴'}]
            lookup['json'] = json.dumps(value)+'\n'
            lookup['stdout_sha256'] = audit.sha(lookup['json'].encode())
        self.reject(audit.inspect_context, ('context',), rewrite, 'actual missing dictionary headword')

    def test_valid_raw_command_cannot_be_globally_forbidden(self):
        self.reject(audit.inspect_context, ('context', 'records', 0), lambda r: r.update(raw_word_command_licence='globally forbidden'), 'valid raw ambiguity not globally forbidden')

    def test_reference_cannot_claim_successful_direct_retrieval(self):
        self.reject(audit.inspect_context, ('context', 'primary_lexical_reference'), lambda r: r.update(retrieval='direct fetch succeeded'), 'bounded actual reference retrieval')


if __name__ == '__main__':
    unittest.main()
