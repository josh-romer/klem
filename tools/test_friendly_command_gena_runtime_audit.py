"""Corrupt actual Gena captures without weakening their historical assertions."""
import copy
import json
import unittest

import friendly_command_gena_runtime_audit as audit
import friendly_command_gena_revision as revision


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
        self.reject(lambda v: revision.inspect(v['revision']), ('revision',*path), change, reason)

    def test_complete_original_captures(self):
        result = audit.inspect(self.values)
        self.assertEqual(result['changed_gold_rows'], 0)
        self.assertEqual(result['new_unjudged_history_paths'], 11)
        self.assertFalse(result['full_coverage_complete'])

    def test_unknown_current_source(self):
        self.revision_reject(('current',),lambda r:r.update({'src/lib.rs':'changed'}),'current complete Gena production closure')

    def test_compiled_json_missing(self):
        self.revision_reject(('binding','production_inputs'),lambda r:r.pop('src/dictionary/proper_names.json'),'complete44')

    def test_hidden_rust_failure(self):
        self.revision_reject(('full','rust_totals'),lambda r:r.update(failed=1),'complete1200')

    def test_failed_queue_receipt_rewritten(self):
        self.revision_reject(('full',),lambda r:r.update(state='passed'),'actual terminal Gena scope')

    def test_queue_recovery_hides_failure(self):
        self.revision_reject(('recovery','results',0),lambda r:r.update(exit_code=1),'actual queue recovery commands')

    def test_queue_recovery_changes_code(self):
        self.revision_reject(('recovery','frozen_inputs'),lambda r:r.update({'src/grammar.rs':'changed'}),'every passing Rust input retained')

    def test_production_changes_relabelled(self):
        self.revision_reject(('binding','individual_production_changes'),lambda r:r.pop('src/engine.rs'),'exact five Gena production changes')

    def test_original_cli_executable_not_protected(self):
        self.revision_reject(('binding','protected_prior_cli_server'),lambda r:r.update({self.values['revision']['binding']['binaries']['klem']['path']:'changed'}),'original CLI/server protected')

    def test_actual_source_freeze_missing(self):
        self.revision_reject(('binding',),lambda r:r.update(index_unchanged=False),'unchanged captured Gena')

    def test_cli_executable_binding_changed(self):
        self.reject(audit.inspect_streams,('streams','external_inputs'),lambda r:r.update({self.values['revision']['binding']['binaries']['klem']['path']:'changed'}),'exact compiled Gena executable')

    def test_cli_policy_missing(self):
        self.reject(audit.inspect_streams,('captures','captures'),lambda r:r.pop(),'all36 current policies')

    def test_cli_context_cropped(self):
        self.reject(audit.inspect_streams,('captures','captures',0),lambda r:r.update(input='앉게나'),'every full original input/policy')

    def test_cli_filter_command_changed(self):
        self.reject(audit.inspect_streams,('captures','captures',0,'command'),lambda r:r.append('--dict-only'),'actual bound CLI filter/cache command')

    def test_cli_span_changed_even_with_refreshed_stdout(self):
        def change(run):
            run['frames'][0]['span']['start'] += 1
            run['stdout'] = ''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in run['frames'])
        self.reject(audit.inspect_streams,('captures','captures',0),change,'contiguous original UTF-8/NFD spans')

    def test_cli_old_candidate_lost_even_with_refreshed_stdout(self):
        def change(run):
            next(f for f in run['frames'] if f['kind']=='word')['analysis']['analyses'].pop(0)
            run['stdout'] = ''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in run['frames'])
        self.reject(audit.inspect_streams,('captures','captures',0),change,'every original candidate and order')

    def test_cli_observation_borrows_other_occurrence(self):
        self.reject(audit.inspect_streams,('captures','captures',0,'observations',0),lambda r:r.update(case_id='borrowed'),'all independently rederived CLI observations')

    def test_primary_native_note_changed(self):
        ident = next(iter(self.values['captures']['native_entries']))
        self.reject(audit.inspect_streams,('captures','native_entries',ident,'response','entry'),lambda r:r.update(notes=['invented']),'every full original primary Native response')

    def test_cohort_partition_missing(self):
        self.reject(audit.inspect_cohorts,('cohorts','runs'),lambda r:r.pop(),'all53502 original cohort words')

    def test_cohort_order_lost(self):
        run = self.values['cohorts']['runs'][0]
        surface = next(s for s,w in run['captures'][1]['words'].items() if len(w['analyses'])>1)
        self.reject(audit.inspect_cohorts,('cohorts','runs',0,'captures',1,'words',surface,'analyses'),lambda r:r.reverse(),'every original candidate and order')

    def test_history_allowance_claims_pre_runtime(self):
        self.reject(audit.inspect_history,('history',),lambda r:r.update(observations_precede_runtime=True),'exact captured finite history fixture')

    def test_unlisted_history_path_is_not_accepted(self):
        self.reject(audit.inspect_cohorts,('cohorts','individual_changed_words',0,'new_paths'),lambda r:r.pop(),'every exact unjudged cohort addition')

    def test_history_fixture_rewritten(self):
        self.reject(audit.inspect_history,('history_fixture','individual_additions',0,'analysis','rules'),lambda r:r.append('invented'),'exact captured finite history fixture')

    def test_original_history_source_modified(self):
        self.reject(audit.inspect_history,('history_sources',),lambda r:r.update({'tests/fixtures/deoniman-sources.json':b'{}'}),'all44 unchanged original history sources')

    def test_gold_partition_missing(self):
        self.reject(audit.inspect_gold,('gold','runs'),lambda r:r.pop(),'all four original annotated partitions')

    def test_gold_changed_even_with_refreshed_stdout_digest(self):
        def change(run):
            rows = [json.loads(s) for s in run['jsonl'].splitlines()]; rows[1]['expected']=['invented']
            run['jsonl']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows);run['stdout_sha256']=audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_gold,('gold','runs',0),change,'every full original annotated row/outcome')

    def test_gold_outcome_changed_even_with_refreshed_digest(self):
        def change(run):
            rows = [json.loads(s) for s in run['jsonl'].splitlines()]; rows[1]['matched']=not rows[1]['matched']
            run['jsonl']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows);run['stdout_sha256']=audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_gold,('gold','runs',0),change,'every full original annotated row/outcome')

    def test_gold_changed_recall_summary(self):
        def change(run):
            rows = [json.loads(s) for s in run['jsonl'].splitlines()]; rows[0]['lemma_recall']=0.0
            run['jsonl']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows);run['stdout_sha256']=audit.sha(run['jsonl'].encode())
        self.reject(audit.inspect_gold,('gold','runs',0),change,'only derived mean-candidate summary differences')

    def test_broad_policy_missing(self):
        self.reject(audit.inspect_broad,('broad','runs'),lambda r:r.pop(),'all eight complete broad streams')

    def test_broad_original_baseline_replaced(self):
        self.reject(audit.inspect_broad,('broad','runs',3),lambda r:r.update(before_jsonl_sha256='invented'),'complete original broad baseline digest')

    def test_broad_occurrence_omitted(self):
        self.reject(audit.inspect_broad,('broad','runs',3,'changed_frames'),lambda r:r.pop(),'all exact per-policy broad additions')

    def test_broad_context_cropped(self):
        self.reject(audit.inspect_broad,('broad','runs',3,'changed_frames',0),lambda r:r.update(complete_original_line='보게나'),'complete original broad context line')

    def test_broad_old_candidate_missing(self):
        self.reject(audit.inspect_broad,('broad','runs',3,'changed_frames',0,'after','analysis','analyses'),lambda r:r.pop(0),'every original candidate and order')

    def test_broad_old_native_conflict_modified(self):
        change = self.values['broad']['runs'][3]['changed_frames'][0]
        index = change['after']['analysis']['analyses'].index(change['before']['analysis']['analyses'][0])
        self.reject(audit.inspect_broad,('broad','runs',3,'changed_frames',0,'after','dictionary','readings',index),lambda r:r.update(status='invented'),'every original Native assessment')

    def test_broad_unjudged_path_claims_correctness(self):
        self.reject(audit.inspect_broad,('broad','runs',3,'changed_frames',0),lambda r:r.update(contextual_verdict='required'),'all new broad hypotheses remain unjudged')

    def test_extra_native_owner_missing(self):
        self.reject(audit.inspect_native,('native','complete_native_entries'),lambda r:r.pop(next(iter(r))),'all42 complete original Native import projections')

    def test_extra_native_full_fields_changed(self):
        ident = next(iter(self.values['native']['complete_native_entries']))
        self.reject(audit.inspect_native,('native','complete_native_entries',ident),lambda r:r.update(notes=['invented']),'all42 complete original Native import projections')

    def test_new_hypothetical_head_omitted(self):
        self.reject(audit.inspect_native,('native','selected_heads'),lambda r:r.pop(),'every newly observed lemma head')

    def test_same_head_homonym_missing(self):
        def change(row):
            value=json.loads(row['stdout']);value['entries'].pop();row['stdout']=json.dumps(value,ensure_ascii=False)+'\n'
        self.reject(audit.inspect_native,('native','actual_headword_queries','가다'),change,'every same-head Native homonym')

    def test_hypothetical_paths_claim_review(self):
        self.reject(audit.inspect_native,('native',),lambda r:r.update(independent_review='complete'),'unmatched hypotheses and independent review remain unjudged')


if __name__ == '__main__':
    unittest.main()
