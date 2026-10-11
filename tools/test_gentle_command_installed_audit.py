"""Reject erased installed policies, rewritten gold and misleading UI claims."""
import copy
import unittest

import gentle_command_installed_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self,check,path,change,reason):
        values = self.values.copy();node = values
        for key in path[:-1]:
            node[key] = copy.copy(node[key]);node = node[key]
        node[path[-1]] = copy.deepcopy(node[path[-1]])
        change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError,reason):check(values)

    def test_complete_original_proof(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['release_rust'],result['policy_decisions']),(1182,138))
        self.assertFalse(result['full_coverage_complete'])

    def test_failed_build_cannot_be_declared_successful(self):
        self.reject(audit.inspect_packages,('failures',0),lambda r:r.update(state='passed'),'both actual failed attempts retained')

    def test_source_freeze_cannot_be_broken(self):
        self.reject(audit.inspect_packages,('installed',),lambda r:r.update(source_unchanged=False),'actual frozen installed source')

    def test_package_cannot_be_omitted(self):
        self.reject(audit.inspect_packages,('package','outputs'),lambda r:r.pop(),'four actual built Nix packages')

    def test_release_failure_cannot_be_hidden(self):
        self.reject(audit.inspect_packages,('installed','release_rust'),lambda r:r['totals'].update(failed=1),'complete actual release Rust suite')

    def test_compiled_data_cannot_be_changed(self):
        self.reject(audit.inspect_packages,('installed','profiles','klem','files'),lambda r:r.update({'src/dictionary/proper_names.json':'changed'}),'all44actual compiled Rust/data inputs')

    def test_frontend_source_cannot_differ(self):
        self.reject(audit.inspect_packages,('current_frontend',),lambda r:r.update({next(iter(r)):'changed'}),'actual complete current frontend source')

    def test_unrecorded_catalog_revision_cannot_replace_captured_long_label(self):
        self.reject(audit.inspect_packages,('current_frontend',),lambda r:r.update({'src/grammar-labels.json':'unrecorded'}),'actual complete current frontend source')

    def test_installed_binary_cannot_be_replaced(self):
        self.reject(audit.inspect_packages,('installed','binaries','klem'),lambda r:r.update(path='/wrong/klem'),'actual bound immutable binaries')

    def test_selected_source_controls_cannot_be_invented(self):
        self.reject(audit.inspect_packages,('selected',),lambda r:r.update(controls=34),'actual selected-source35control proof')

    def test_installed_source_policy_cannot_disappear(self):
        self.reject(audit.inspect_installed,('installed','source_runs'),lambda r:r.pop(),'all original installed comparison policies')

    def test_original_source_group_cannot_be_cropped(self):
        self.reject(audit.inspect_installed,('installed','source_runs',0),lambda r:r['original_capture'].update(input_text='오렴'),'complete unchanged audited original capture')

    def test_actual_filter_command_cannot_change(self):
        self.reject(audit.inspect_installed,('installed','source_runs',0),lambda r:r['command'].append('--dict-only'),'actual installed comparison command')

    def test_complete_native_response_cannot_change(self):
        self.reject(audit.inspect_installed,('installed','native_records',0),lambda r:r.update(stdout='{}'),'every actual installed output byte')

    def test_original_annotated_rows_cannot_change(self):
        self.reject(audit.inspect_installed,('installed','corpus_runs',0),lambda r:r.update(stdout='{}'),'every actual installed output byte')

    def test_broad_policy_cannot_disappear(self):
        self.reject(audit.inspect_installed,('installed','broad_runs'),lambda r:r.pop(),'all eight installed broad streams')

    def test_full_broad_output_checksum_cannot_change(self):
        self.reject(audit.inspect_installed,('installed','broad_runs',0),lambda r:r.update(stdout_sha256='changed'),'whole installed broad output and original input bytes')

    def test_novel_context_cannot_be_cropped(self):
        self.reject(audit.inspect_installed,('installed','broad_runs',3),lambda r:r['changed_frames'][0].update(complete_original_line='주렴'),'every unchanged original novel hypothesis/context')

    def test_browser_error_cannot_be_hidden(self):
        self.reject(audit.inspect_browser,('browser','errors'),lambda r:r.append('error'),'actual error-free installed browser')

    def test_owned_server_cannot_remain_running(self):
        self.reject(audit.inspect_browser,('browser_runtime',),lambda r:r.update(server_stopped=False),'actual owned server stopped cleanly')

    def test_unexpected_server_signal_cannot_be_accepted(self):
        self.reject(audit.inspect_browser,('browser_runtime',),lambda r:r.update(server_exit_code=-9),'actual owned server stopped cleanly')

    def test_api_byte_span_cannot_shift(self):
        self.reject(audit.inspect_browser,('browser','responses',0),lambda r:r['api']['records'][0]['span'].update(start=1),'all original browser API frames/spans/candidates')

    def test_label_cannot_borrow_willingness_owner(self):
        self.reject(audit.inspect_browser,('browser','responses',0),lambda r:r['api']['grammar']['-으렴'][0].update(id='krdict:76564'),'both exact original browser ending owners')

    def test_dropdown_cannot_invent_a_reading(self):
        self.reject(audit.inspect_browser,('browser','policyDecisions',0),lambda r:r['offered_indices'].append('999'),'every original offered reading matches actual CLI policy')

    def test_forbidden_path_cannot_be_offered(self):
        self.reject(audit.inspect_browser,('browser','policyDecisions',14),lambda r:r.update(allowed=True),'every forbidden path remains absent')

    def test_normalized_component_order_cannot_change(self):
        self.reject(audit.inspect_browser,('browser','diagrams',0),lambda r:r['forms'].reverse(),'independent canonical component order')

    def test_label_attribution_cannot_disappear(self):
        self.reject(audit.inspect_browser,('browser','diagrams',0),lambda r:r.update(source_hint='unattributed'),'original ending label attribution')

    def test_export_cannot_drop_original_frames(self):
        self.reject(audit.inspect_browser,('browser','exports',0),lambda r:r['records'].pop(),'six complete exact browser exports')

    def test_native_endpoint_cannot_drop_fields(self):
        self.reject(audit.inspect_browser,('browser','nativeEntries',0),lambda r:r['entry'].update(notes=[]),'all47completeoriginalbrowserNativefields')


if __name__ == '__main__':
    unittest.main()
