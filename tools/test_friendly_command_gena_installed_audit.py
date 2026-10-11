"""Corruption controls for actual installed Gena packages and browser captures."""
import copy
import json
import unittest

import friendly_command_gena_installed_audit as audit


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
        self.assertEqual(result['annotated_gold_rows'],66570)
        self.assertFalse(result['full_coverage_complete'])

    def test_wrong_package_checkpoint(self):
        self.reject(audit.inspect_packages,('package',),lambda r:r.update(head='unrelated'),'same named installed checkpoint')

    def test_failed_package_build(self):
        self.reject(audit.inspect_packages,('package',),lambda r:r.update(exit_code=1),'all four actual installed outputs')

    def test_missing_package_output(self):
        self.reject(audit.inspect_packages,('package','outputs'),lambda r:r.pop(),'all four actual installed outputs')

    def test_source_selection_missing_file(self):
        self.reject(audit.inspect_packages,('selected','selected_files'),lambda r:r.pop(next(iter(r))),'complete6985/6943')

    def test_source_profile_loses_compiled_json(self):
        self.reject(audit.inspect_packages,('installed','profiles','klem','files'),lambda r:r.pop('src/dictionary/proper_names.json'),'complete selected/installed source profile equality')

    def test_installed_executable_binding_changed(self):
        self.reject(audit.inspect_packages,('installed','binaries','klem'),lambda r:r.update(sha256='changed'),'exact actual installed executable')

    def test_hidden_release_rust_failure(self):
        self.reject(audit.inspect_packages,('installed','release_rust','totals'),lambda r:r.update(failed=1),'release totals match full package log')

    def test_cli_policy_omitted(self):
        self.reject(audit.inspect_runtime,('installed','source_runs'),lambda r:r.pop(),'all36 complete installed policies')

    def test_cli_output_changed_with_updated_digest(self):
        def change(row):
            frames=[json.loads(s) for s in row['stdout'].splitlines()]
            next(f for f in frames if f['kind']=='word')['analysis']['analyses'].pop(0)
            row['stdout']=''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in frames);row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_runtime,('installed','source_runs',0),change,'every original installed CLI byte')

    def test_native_complete_owner_omitted(self):
        self.reject(audit.inspect_runtime,('installed','native_records'),lambda r:r.pop(),'all44 complete installed Native owners')

    def test_native_notes_changed_even_with_updated_digest(self):
        def change(row):
            value=json.loads(row['stdout']);value['entry']['notes']=['invented'];row['stdout']=json.dumps(value,ensure_ascii=False)+'\n';row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_runtime,('installed','native_records',0),change,'every complete original installed Native response')

    def test_new_hypothetical_head_lookup_omitted(self):
        self.reject(audit.inspect_runtime,('installed','lookup_records'),lambda r:r.pop(),'all69 installed new lemma lookups')

    def test_lookup_homonym_missing(self):
        def change(row):
            value=json.loads(row['stdout']);value['entries'].pop();row['stdout']=json.dumps(value,ensure_ascii=False)+'\n'
        self.reject(audit.inspect_runtime,('installed','lookup_records',0),change,'every complete installed headword response')

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
        self.reject(audit.inspect_runtime,('installed','corpus_runs',0),change,'every complete installed gold row/outcome/summary')

    def test_broad_policy_omitted(self):
        self.reject(audit.inspect_runtime,('installed','broad_runs'),lambda r:r.pop(),'all eight installed broad streams')

    def test_broad_candidate_output_replaced(self):
        self.reject(audit.inspect_runtime,('installed','broad_runs',3),lambda r:r.update(stdout_sha256='changed'),'complete installed broad input/output bytes')

    def test_broad_original_context_cropped(self):
        self.reject(audit.inspect_runtime,('installed','broad_runs',3,'changed_frames',0),lambda r:r.update(complete_original_line='보게나'),'all18 full original unjudged broad contexts')

    def test_owned_installed_server_not_stopped(self):
        self.reject(audit.inspect_browser,('browser_runtime',),lambda r:r.update(server_stopped=False),'owned installed browser source freeze/shutdown')

    def test_browser_uses_wrong_launcher(self):
        self.reject(audit.inspect_browser,('browser_runtime','command'),lambda r:r.__setitem__(0,'unrelated'),'actual packaged launcher browser command')

    def test_browser_native_owner_missing(self):
        self.reject(audit.inspect_browser,('browser','nativeEntries'),lambda r:r.pop(),'every independently audited original installed browser choice')

    def test_browser_component_order_changed(self):
        self.reject(audit.inspect_browser,('browser','diagrams',0,'forms'),lambda r:r.reverse(),'every independently audited original installed browser choice')

    def test_browser_offered_option_missing(self):
        self.reject(audit.inspect_browser,('browser','policyDecisions',0,'offered_indices'),lambda r:r.pop(),'every independently audited original installed browser choice')

    def test_browser_export_candidate_omitted(self):
        self.reject(audit.inspect_browser,('browser','exports',0,'records',0,'analysis','analyses'),lambda r:r.pop(0),'every independently audited original installed browser choice')

    def test_served_asset_changed(self):
        self.reject(audit.inspect_browser,('browser_runtime','served_assets',0),lambda r:r.update(sha256='changed'),'actual installed served assets')


if __name__=='__main__':
    unittest.main()
