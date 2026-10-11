"""Reject corruption of actual current installed outputs and browser decisions."""
import copy
import json
import unittest

import gentle_command_long_installed_audit as audit


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

    def test_complete_actual_current_evidence(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['release_rust'], result['policy_decisions']), (1191,402))
        self.assertFalse(result['full_coverage_complete'])

    def test_build_source_freeze(self):
        self.reject(audit.inspect_packages,('installed',),lambda r:r.update(source_unchanged=False),'complete actual installed source freeze')

    def test_exact_installed_checkpoint(self):
        self.reject(audit.inspect_packages,('package',),lambda r:r.update(head='6413c1b'),'one exact current installed checkpoint')

    def test_all_four_packages(self):
        self.reject(audit.inspect_packages,('package','outputs'),lambda r:r.pop(),'all four actual current packages')

    def test_inventory_source_byte(self):
        self.reject(audit.inspect_packages,('package','inventory_source_files'),lambda r:r.update({'src/lib.rs':'changed'}),'every selected inventory source byte')

    def test_failed_attempt_preserved(self):
        self.reject(audit.inspect_packages,('failures',0),lambda r:r.update(state='passed'),'both actual failed build attempts retained')

    def test_original_build_log(self):
        self.reject(audit.inspect_packages,('failures',1),lambda r:r.update(log_sha256='changed'),'all original build logs retained')

    def test_actual_release_test_counts(self):
        self.reject(audit.inspect_packages,('installed','release_rust'),lambda r:r['totals'].update(failed=1),'complete current release Rust suite')

    def test_compiled_source_byte(self):
        self.reject(audit.inspect_packages,('installed','profiles','klem','files'),lambda r:r.update({'src/lib.rs':'changed'}),'every original Nix package source byte')

    def test_frontend_source_byte(self):
        self.reject(audit.inspect_packages,('current_frontend',),lambda r:r.update({'src/grammar-labels.json':'changed'}),'all18current frontend sources')

    def test_replaced_installed_executable(self):
        self.reject(audit.inspect_packages,('installed','binaries','klem'),lambda r:r.update(path='/wrong/klem'),'exact immutable installed executables')

    def test_missing_source_policy(self):
        self.reject(audit.inspect_installed,('installed','source_runs'),lambda r:r.pop(),'all current installed original comparison policies')

    def test_cropped_original_source(self):
        self.reject(audit.inspect_installed,('installed','source_runs',0),lambda r:r['original_capture'].update(input_text='오려무나'),'every complete unchanged original capture')

    def test_original_filter_command(self):
        self.reject(audit.inspect_installed,('installed','source_runs',0),lambda r:r['command'].append('--dict-only'),'actual installed original policy command')

    def test_all_native_fields(self):
        self.reject(audit.inspect_installed,('installed','native_records',0),lambda r:r.update(stdout='{}'),'every installed source Native and gold output byte')

    def test_gold_cannot_change_with_refreshed_checksum(self):
        def change(row):
            frames = [json.loads(line) for line in row['stdout'].splitlines()]
            frames[1]['expected']=['invented']
            row['stdout']=''.join(json.dumps(frame,ensure_ascii=False)+'\n' for frame in frames)
            row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_installed,('installed','corpus_runs',0),change,'every installed source Native and gold output byte')

    def test_all_broad_policies(self):
        self.reject(audit.inspect_installed,('installed','broad_runs'),lambda r:r.pop(),'all eight current installed broad policies')

    def test_whole_broad_output(self):
        self.reject(audit.inspect_installed,('installed','broad_runs',0),lambda r:r.update(stdout_sha256='changed'),'whole original installed broad input and output')

    def test_original_novel_context(self):
        self.reject(audit.inspect_installed,('installed','broad_runs',3),lambda r:r['changed_frames'][0].update(complete_original_line='읽으려무나'),'every original novel occurrence candidate owner and context')

    def test_all_extra_policies(self):
        self.reject(audit.inspect_extra,('installed','extra_runs'),lambda r:r.pop(),'all12additional Unicode filter cache policies')

    def test_extra_case_input(self):
        self.reject(audit.inspect_extra,('installed','extra_runs',0),lambda r:r.update(input_text='읽으려무나'),'every original additional case input byte')

    def test_extra_span_with_refreshed_checksum(self):
        def change(row):
            frames=[json.loads(line) for line in row['stdout'].splitlines()]
            frames[0]['span']['start']=1
            row['stdout']=''.join(json.dumps(frame,ensure_ascii=False)+'\n' for frame in frames)
            row['stdout_sha256']=audit.sha(row['stdout'].encode())
        self.reject(audit.inspect_extra,('installed','extra_runs',0),change,'complete contiguous original UTF8 spans')

    def test_extra_stable_judgment_index(self):
        self.reject(audit.inspect_extra,('installed','extra_runs',0),lambda r:r['observations'][0].update(record_index=2),'every independently rederived additional judgment index')

    def test_browser_error(self):
        self.reject(audit.inspect_browser,('browser','errors'),lambda r:r.append('error'),'actual error-free current installed browser')

    def test_owned_server_stop(self):
        self.reject(audit.inspect_browser,('browser_runtime',),lambda r:r.update(server_stopped=False),'actual owned browser server stopped cleanly')

    def test_unexpected_server_exit(self):
        self.reject(audit.inspect_browser,('browser_runtime',),lambda r:r.update(server_exit_code=-9),'actual owned browser server stopped cleanly')

    def test_actual_browser_producer(self):
        self.reject(audit.inspect_browser,('browser_runtime','driver'),lambda r:r.update(text='invented'),'complete actual browser producers')

    def test_served_asset_binding(self):
        self.reject(audit.inspect_browser,('browser_runtime','served_assets',0),lambda r:r.update(sha256='changed'),'actual immutable served SolidJS assets')

    def test_api_original_span(self):
        self.reject(audit.inspect_browser,('browser','responses',0),lambda r:r['api']['records'][0]['span'].update(start=1),'complete contiguous original UTF8 spans')

    def test_borrowed_ending_rule(self):
        self.reject(audit.inspect_browser,('browser','responses',0),lambda r:r['api']['rules'].pop('ending.gentle_command_long'),'all separate current browser grammar rules')

    def test_invented_dropdown_option(self):
        self.reject(audit.inspect_browser,('browser','policyDecisions',0),lambda r:r['offered_indices'].append('999'),'every independently filtered browser option')

    def test_forbidden_browser_choice(self):
        index=next(i for i,r in enumerate(self.values['browser']['policyDecisions']) if r.get('verdict')=='forbidden')
        self.reject(audit.inspect_browser,('browser','policyDecisions',index),lambda r:r.update(allowed=True),'all138forbidden browser choices absent')

    def test_required_browser_policy(self):
        self.reject(audit.inspect_browser,('browser','policyDecisions',0),lambda r:r.update(allowed=False),'every required current browser policy')

    def test_rendered_component_order(self):
        self.reject(audit.inspect_browser,('browser','diagrams',0),lambda r:r['forms'].reverse(),'independently ordered canonical browser components')

    def test_original_label_attribution(self):
        self.reject(audit.inspect_browser,('browser','diagrams',0),lambda r:r.update(source_hint='unattributed'),'all individual original browser grammar attributions')

    def test_whole_browser_export(self):
        self.reject(audit.inspect_browser,('browser','exports',0),lambda r:r['records'].pop(),'six independently filtered complete browser exports')

    def test_complete_browser_native_owner(self):
        self.reject(audit.inspect_browser,('browser','nativeEntries',0),lambda r:r['entry'].update(notes=['invented']),'all62complete original Native browser owners')


if __name__ == '__main__':
    unittest.main()
