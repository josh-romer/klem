"""Corruption controls for actual installed Sena packages and browser captures."""
import copy
import json
import unittest

import friendly_hortative_sena_installed_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values=audit.inputs()

    def reject(self,check,path,change,reason):
        values=self.values.copy();node=values
        for key in path[:-1]:
            node[key]=copy.copy(node[key]);node=node[key]
        node[path[-1]]=copy.deepcopy(node[path[-1]]);change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError,reason):check(values)

    def test_complete_original_installed_captures(self):
        result=audit.inspect(self.values)
        type(self).summary=result
        self.assertEqual(result['annotated_gold_rows'],66570)
        self.assertFalse(result['full_coverage_complete'])

    def test_wrong_package_checkpoint(self):
        self.reject(audit.inspect_packages,('package',),lambda r:r.update(head='unrelated'),'same named installed checkpoint')

    def test_failed_package_build(self):
        self.reject(audit.inspect_packages,('package',),lambda r:r.update(exit_code=1),'all four actual installed package outputs')

    def test_missing_package_output(self):
        self.reject(audit.inspect_packages,('package','outputs'),lambda r:r.pop(),'all four actual installed package outputs')

    def test_source_selection_missing_file(self):
        self.reject(audit.inspect_packages,('gate','inventory_source_files'),lambda r:r.pop(next(iter(r))),'complete7216 inventory source bytes')

    def test_source_profile_loses_compiled_json(self):
        self.reject(audit.inspect_packages,('installed','profiles','klem','files'),lambda r:r.pop('src/dictionary/proper_names.json'),'complete selected installed profile equality')

    def test_installed_executable_binding_changed(self):
        self.reject(audit.inspect_packages,('installed','binaries','klem'),lambda r:r.update(sha256='changed'),'exact actual installed executable')

    def test_hidden_release_rust_failure(self):
        self.reject(audit.inspect_packages,('installed','release_rust','totals'),lambda r:r.update(failed=1),'release totals match original Rust log')

    def test_cli_policy_omitted(self):
        self.reject(audit.inspect_runtime,('installed','source_runs'),lambda r:r.pop(),'all36 complete installed policies')

    def test_cli_output_changed_with_updated_digest(self):
        def change(row):
            frames=[json.loads(s) for s in row['stdout'].splitlines()]
            next(f for f in frames if f['kind']=='word')['analysis']['analyses'].pop(0)
            row['stdout']=''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in frames);row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_runtime,('installed','source_runs',0),change,'every original installed CLI byte')

    def test_native_complete_owner_omitted(self):
        self.reject(audit.inspect_runtime,('installed','native_records'),lambda r:r.pop(),'all46 complete installed Native owners')

    def test_native_notes_changed_even_with_updated_digest(self):
        def change(row):
            value=json.loads(row['stdout']);value['entry']['notes']=['invented'];row['stdout']=json.dumps(value,ensure_ascii=False)+'\n';row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_runtime,('installed','native_records',0),change,'every original installed Native byte')

    def test_new_hypothetical_head_lookup_omitted(self):
        self.reject(audit.inspect_runtime,('installed','lookup_records'),lambda r:r.pop(),'all72 complete installed headword queries')

    def test_lookup_homonym_missing(self):
        def change(row):
            value=json.loads(row['stdout']);value['entries'].pop();row['stdout']=json.dumps(value,ensure_ascii=False)+'\n'
        self.reject(audit.inspect_runtime,('installed','lookup_records',0),change,'every original installed headword byte')

    def test_cohort_partition_omitted(self):
        self.reject(audit.inspect_runtime,('installed','cohort_runs'),lambda r:r.pop(),'all53502 installed cohort words')

    def test_cohort_old_candidate_order_changed(self):
        run=self.values['installed']['cohort_runs'][0];surface=next(s for s,w in run['words'].items() if len(w['analyses'])>1)
        self.reject(audit.inspect_runtime,('installed','cohort_runs',0,'words',surface,'analyses'),lambda r:r.reverse(),'every original ordered installed WordAnalysis')

    def test_gold_partition_omitted(self):
        self.reject(audit.inspect_runtime,('installed','corpus_runs'),lambda r:r.pop(),'all four installed gold partitions')

    def test_gold_annotation_changed_with_updated_digest(self):
        def change(row):
            lines=[json.loads(s) for s in row['stdout'].splitlines()];lines[1]['expected']=['invented'];row['stdout']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in lines);row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_runtime,('installed','corpus_runs',0),change,'every complete installed gold row outcome and summary')

    def test_broad_policy_omitted(self):
        self.reject(audit.inspect_runtime,('installed','broad_runs'),lambda r:r.pop(),'all eight installed broad streams')

    def test_broad_candidate_output_replaced(self):
        self.reject(audit.inspect_runtime,('installed','broad_runs',3),lambda r:r.update(stdout_sha256='changed'),'complete installed broad input output bytes')

    def test_broad_original_context_cropped(self):
        self.reject(audit.inspect_runtime,('installed','broad_runs',3,'changed_frames'),lambda r:r.append({'invented':'context'}),'all full original unjudged broad contexts')

    def test_owned_installed_server_not_stopped(self):
        self.reject(audit.inspect_browser,('browser_runtime',),lambda r:r.update(server_stopped=False),'owned installed browser source freeze shutdown')

    def test_browser_uses_wrong_launcher(self):
        self.reject(audit.inspect_browser,('browser_runtime','command'),lambda r:r.__setitem__(0,'unrelated'),'actual packaged launcher browser command')

    def test_browser_native_owner_missing(self):
        self.reject(audit.inspect_browser,('browser','nativeEntries'),lambda r:r.pop(),'every independently audited original installed browser choice form Native export')

    def test_browser_component_order_changed(self):
        self.reject(audit.inspect_browser,('browser','diagrams',0,'forms'),lambda r:r.reverse(),'every independently audited original installed browser choice form Native export')

    def test_browser_offered_option_missing(self):
        self.reject(audit.inspect_browser,('browser','policyDecisions',0,'offered_indices'),lambda r:r.pop(),'every independently audited original installed browser choice form Native export')

    def test_browser_export_candidate_omitted(self):
        self.reject(audit.inspect_browser,('browser','exports',0,'records',0,'analysis','analyses'),lambda r:r.pop(0),'every independently audited original installed browser choice form Native export')

    def test_served_asset_changed(self):
        self.reject(audit.inspect_browser,('browser_runtime','served_assets',0),lambda r:r.update(sha256='changed'),'actual installed served assets')


    def test_actual_four_check_gate_failed(self):
        self.reject(audit.inspect_packages,('gate',),lambda r:r.update(exit_code=1),'actual complete four-check terminal success')

    def test_inventory_check_omitted(self):
        self.reject(audit.inspect_packages,('gate','command'),lambda r:r.pop(),'all four actual Nix checks')

    def test_packaged_launcher_build_omitted(self):
        self.reject(audit.inspect_packages,('package','command'),lambda r:r.pop(),'actual packaged web launcher build')

    def test_original_gate_binding_replaced(self):
        self.reject(audit.inspect_packages,('package',),lambda r:r.update(complete_gate_sha256='changed'),'original complete gate prerequisite')

    def test_parent_debug_executable_unprotected(self):
        path=next(iter(self.values['gate']['protected_binaries']))
        self.reject(audit.inspect_packages,('installed','frozen_inputs'),lambda r:r.__setitem__(path,'changed'),'all six protected original debug executables')

    def test_original_corpus_sentence_policy_omitted(self):
        self.reject(audit.inspect_runtime,('installed','corpus_sentence_runs'),lambda r:r.pop(),'all12 whole original corpus policies')

    def test_original_corpus_stable_case_replaced(self):
        self.reject(audit.inspect_runtime,('installed','corpus_sentence_runs',0),lambda r:r.update(stable_case_id='invented'),'original corpus stable case and full capture')

    def test_original_corpus_ambiguous_candidate_omitted(self):
        def change(row):
            frames=[json.loads(s) for s in row['stdout'].splitlines()]
            next(f for f in frames if f['kind']=='word' and '중세' in f['surface'])['analysis']['analyses'].pop(0)
            row['stdout']=''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in frames)
            row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_runtime,('installed','corpus_sentence_runs',0),change,'every original installed corpus sentence byte')

    def test_browser_corpus_decision_omitted(self):
        self.reject(audit.inspect_browser,('browser','corpusDecisions'),lambda r:r.pop(),'every independently audited original installed browser choice form Native export')

    def test_complete_browser_source_file_omitted(self):
        self.reject(audit.inspect_browser,('browser_runtime','source_inputs'),lambda r:r.pop(next(iter(r))),'same complete installed browser checkpoint')

    def test_own_installed_source_profile_changed(self):
        self.reject(audit.inspect_packages,('installed','profiles','klem','files'),lambda r:r.__setitem__('src/engine.rs','changed'),'complete selected installed profile equality')

    def test_browser_actual_api_candidate_removed(self):
        records=self.values['browser']['responses'][0]['api']['records']
        index=next(i for i,r in enumerate(records) if r['kind']=='word' and r['analysis']['analyses'])
        self.reject(audit.inspect_browser,('browser','responses',0,'api','records',index,'analysis','analyses'),lambda r:r.pop(0),'every complete original installed API field')


    def test_corpus_latency_only_difference_remains_accepted(self):
        v=self.values.copy();v['browser']=copy.deepcopy(v['browser'])
        for row in v['browser']['corpusDecisions']:row['api']['elapsed_ms']=123.456
        audit.inspect_browser(v)

    def test_corpus_semantic_field_cannot_be_lost(self):
        def change(row):row['api'].pop(next(key for key in row['api'] if key!='elapsed_ms'))
        self.reject(audit.inspect_browser,('browser','corpusDecisions',0),change,'every independently audited original corpus semantic field')

    def test_corpus_invalid_latency_cannot_pass(self):
        self.reject(audit.inspect_browser,('browser','corpusDecisions',0,'api'),lambda api:api.update(elapsed_ms=-1),'valid captured corpus latency')


    def test_whole_installed_stream_omitted(self):
        v=self.values.copy();v['originals']=v['originals'].copy()
        name=next(n for n in v['originals'] if n.endswith('retry3-command-0000-stdout.gz'))
        del v['originals'][name]
        with self.assertRaisesRegex(AssertionError,'all complete unique original stream archives'):
            audit.inspect_streams(v)

    def test_whole_installed_stream_corrupted(self):
        v=self.values.copy();v['originals']=v['originals'].copy()
        name=next(n for n in v['originals'] if n.endswith('retry3-command-0000-stdout.gz'))
        v['originals'][name]=b'changed stream'
        with self.assertRaisesRegex(AssertionError,'original packed installed stream bytes'):
            audit.inspect_streams(v)

    def test_original_failed_wrapper_cannot_be_promoted(self):
        import gzip
        v=self.values.copy();v['originals']=v['originals'].copy()
        name=audit.PREFIX+'installed-runtime-retry3.json.gz'
        original=json.loads(gzip.decompress(v['originals'][name]));original['state']='passed'
        v['originals'][name]=gzip.compress(json.dumps(original).encode(),mtime=0)
        with self.assertRaisesRegex(AssertionError,'original failed wrapper retained separately'):
            audit.inspect_streams(v)


if __name__=='__main__':
    unittest.main()
