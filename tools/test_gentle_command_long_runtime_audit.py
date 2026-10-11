"""Corrupt real captures to verify that the new revision audit rejects them."""
import copy
import json
import unittest

import gentle_command_long_runtime_audit as audit
import gentle_command_long_revision as revision


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self, check, path, change, reason):
        values = self.values.copy(); node = values
        for key in path[:-1]:
            node[key] = copy.copy(node[key]); node = node[key]
        node[path[-1]] = copy.deepcopy(node[path[-1]])
        change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError, reason): check(values)

    def revision_reject(self, path, change, reason):
        self.reject(lambda v: revision.inspect(v['revision']), ('revision', *path), change, reason)

    def test_complete_original_capture(self):
        result = audit.inspect(self.values)
        self.assertEqual(result['unique_native_owners'], 48)
        self.assertEqual(result['other_raw_novel_additions_unjudged'], 11)
        self.assertFalse(result['full_coverage_complete'])

    def test_unrelated_current_source_edit(self):
        self.revision_reject(('current',), lambda r: r.update({'src/lib.rs': 'changed'}), 'current complete named production closure')

    def test_compiled_json_missing(self):
        self.revision_reject(('binding', 'production_inputs'), lambda r: r.pop('src/dictionary/proper_names.json'), 'complete44-input')

    def test_failed_full_suite(self):
        self.revision_reject(('full',), lambda r: r.update(state='failed'), 'terminal named production')

    def test_full_suite_hides_failure(self):
        self.revision_reject(('full', 'totals'), lambda r: r.update(failed=1), 'complete original revision Rust')

    def test_refresh_earlier_running_receipt(self):
        self.revision_reject(('binding',), lambda r: r.update(observed_full_rust_state='passed'), 'historical running receipt')

    def test_production_changes_cannot_be_relabeled(self):
        self.revision_reject(('binding', 'individual_production_changes'), lambda r: r.pop('src/grammar.rs'), 'exact five declared')

    def test_missing_source_freeze(self):
        self.revision_reject(('full',), lambda r: r.update(index_unchanged=False), 'complete revision source freeze')

    def test_changed_runtime_executable(self):
        self.reject(audit.inspect_streams, ('streams', 'frozen_inputs'), lambda r: r.update({self.values['revision']['binding']['binaries']['klem']['path']: 'changed'}), 'exact compiled runtime executable')

    def test_source_policy_missing(self):
        self.reject(audit.inspect_streams, ('streams', 'runs'), lambda r: r.pop(), 'all36complete source policies')

    def test_source_command_filter_changed(self):
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), lambda r: r['command'].append('--dict-only'), 'actual source filter/cache')

    def test_source_context_cropped(self):
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), lambda r: r.update(input_text='오려무나'), 'complete original source bytes')

    def test_source_span_changed_with_refreshed_digest(self):
        def change(run):
            rows = [json.loads(line) for line in run['jsonl'].splitlines()]
            rows[0]['span']['start'] += 1
            run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows)
            run['jsonl_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), change, 'contiguous original source spans')

    def test_source_observation_borrows_another_occurrence(self):
        self.reject(audit.inspect_streams, ('streams', 'runs', 0), lambda r: r['observations'][0].update(record_index=0), 'all492individually')

    def test_judgments_silently_promoted(self):
        self.reject(audit.inspect_streams, ('streams',), lambda r: r.update(linguistic_judgments_promoted=True), 'private judgments not silently promoted')

    def test_native_owner_missing(self):
        self.reject(audit.inspect_native, ('native', 'records'), lambda r: r.pop(), 'all complete Native owners')

    def test_native_notes_rewritten(self):
        self.reject(audit.inspect_native, ('novel_native', 'records', 0), lambda r: r['complete_original_entry'].update(notes=['invented']), 'all original Native fields')

    def test_native_cli_wrong_owner(self):
        self.reject(audit.inspect_native, ('native', 'records', 0), lambda r: r['captures'][0]['command'].__setitem__(-1, 'krdict:1'), 'actual bound Native CLI and owner')

    def test_missing_cohort_partition(self):
        self.reject(audit.inspect_cohorts, ('cohorts', 'runs'), lambda r: r.pop(), 'all53502original')

    def test_history_candidate_order_changed(self):
        def change(run):
            words = run['captures'][1]['words']
            next(word for word in words.values() if len(word['analyses']) > 1)['analyses'].reverse()
        self.reject(audit.inspect_cohorts, ('cohorts', 'runs', 1), change, 'every complete ordered original WordAnalysis')

    def test_gold_partition_missing(self):
        self.reject(audit.inspect_gold, ('gold', 'runs'), lambda r: r.pop(), 'all four original annotated')

    def test_gold_changed_even_with_refreshed_hashes(self):
        def change(run):
            rows = [json.loads(line) for line in run['jsonl'].splitlines()]
            rows[1]['expected'] = ['invented']
            run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows)
            run['stdout_sha256'] = run['before_stdout_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_gold, ('gold', 'runs', 0), change, 'every original annotated output byte')

    def test_broad_policy_missing(self):
        self.reject(audit.inspect_broad, ('broad', 'runs'), lambda r: r.pop(), 'all eight complete broad streams')

    def test_broad_parent_baseline_replaced(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 3), lambda r: r.update(before_jsonl_sha256='changed'), 'exact complete prior broad baseline')

    def test_novel_occurrence_missing(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 3), lambda r: r['changed_frames'].pop(), 'every exact original novel occurrence')

    def test_original_novel_context_cropped(self):
        self.reject(audit.inspect_broad, ('broad', 'runs', 3, 'changed_frames', 0), lambda r: r.update(complete_original_line='읽으려무나'), 'complete original novel context')

    def test_old_candidate_lost(self):
        def change(record):
            record['after']['analysis']['analyses'].remove(record['before']['analysis']['analyses'][0])
        self.reject(audit.inspect_broad, ('broad', 'runs', 3, 'changed_frames', 0), change, 'every original candidate and order')

    def test_old_native_assessment_rewritten(self):
        def change(r):
            old_path = r['before']['analysis']['analyses'][0]
            index = r['after']['analysis']['analyses'].index(old_path)
            r['after']['dictionary']['readings'][index]['status'] = 'invented'
        self.reject(audit.inspect_broad, ('broad', 'runs', 3, 'changed_frames', 0), change, 'every original Native assessment')

    def test_novel_proposal_claims_pre_observation(self):
        self.reject(audit.inspect_novel, ('novel',), lambda r: r.update(proposals_precede_runtime=True), 'honest post-observation')

    def test_novel_proposal_borrows_other_context(self):
        self.reject(audit.inspect_novel, ('novel', 'items', 0), lambda r: r.update(complete_original_line=self.values['novel']['items'][1]['complete_original_line']), 'every full original novel context')

    def test_lexical_homonym_missing(self):
        self.reject(audit.inspect_novel, ('novel', 'items', 2), lambda r: r['lexical_owner_ids'].pop(), 'every complete lexical homonym owner')

    def test_observed_hypotheses_claim_independent_review(self):
        self.reject(audit.inspect_novel, ('novel', 'items', 0), lambda r: r.update(independent_review='complete'), 'independent review pending')

    def test_additional_regressions_hide_failure(self):
        self.reject(audit.inspect_validation, ('validation', 'rust_totals'), lambda r: r.update(failed=1), 'actual additional18Rust45controls')

    def test_original_compile_failure_not_preserved(self):
        self.reject(audit.inspect_validation, ('proof', 'gentle-command-long-interaction-compile-failure.json'), lambda r: r.update(actual_exit_code=0), 'original interaction compile failure preserved')


if __name__ == '__main__':
    unittest.main()
