"""Reject false performance claims, missing policies and altered bindings."""
import copy
import unittest
import friendly_command_gena_performance_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self,check,path,change,reason):
        value = self.values.copy()
        node = value
        for key in path[:-1]:
            node[key] = copy.copy(node[key])
            node = node[key]
        node[path[-1]] = copy.deepcopy(node[path[-1]])
        change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError,reason):
            check(value)

    def test_original_complete_performance(self):
        type(self).summary = audit.inspect(self.values)
        self.assertEqual(type(self).summary['samples'],80)
        self.assertFalse(type(self).summary['host_isolation_proved'])

    def test_failed_measurement_receipt(self):
        self.reject(audit.inspect_binding,('report',),lambda r:r.update(exit_code=1),'actual terminal unchanged timings')

    def test_wrong_source_checkpoint(self):
        self.reject(audit.inspect_binding,('report',),lambda r:r.update(captured_head='unrelated'),'complete6985 original Gena source checkpoint')

    def test_source_file_missing(self):
        self.reject(audit.inspect_binding,('report','source_inputs'),lambda r:r.pop(next(iter(r))),'complete6985 original Gena source checkpoint')

    def test_wrong_installed_binary(self):
        self.reject(audit.inspect_binding,('report',),lambda r:r.update(cli_sha256='changed'),'exact distinct release executable pair')

    def test_compiled_json_missing(self):
        self.reject(audit.inspect_binding,('report','after_profile'),lambda r:r.pop('src/dictionary/proper_names.json'),'every original installed compile profile')

    def test_unknown_compiled_change(self):
        self.reject(audit.inspect_binding,('report','individual_compiled_changes'),lambda r:r.append('src/normalize.rs'),'exact five compiled timing changes')

    def test_changed_dictionary(self):
        self.reject(audit.inspect_binding,('report',),lambda r:r.update(dictionary_sha256='changed'),'unchanged full imported timing dictionary')

    def test_missing_physical_proof(self):
        self.reject(audit.inspect_binding,('physical',),lambda r:r.pop(next(iter(r))),'all13 original timing input bindings')

    def test_false_live_executable_claim(self):
        self.reject(audit.inspect_binding,('binary_evidence',),lambda r:r.update(live_executable_files_verified=True),'honest captured timing executable scope')

    def test_multiple_cpus_claimed(self):
        self.reject(audit.inspect_samples,('report','cpu_affinity'),lambda r:r.append(999),'one allowed CPU')

    def test_own_job_recorded(self):
        self.reject(audit.inspect_samples,('report','workloads',0,'samples',0,'start_context','active_own_jobs'),lambda r:r.append({'pid':123}),'all original timing contexts')

    def test_workload_missing(self):
        self.reject(audit.inspect_samples,('report','workloads'),lambda r:r.pop(),'all eight full novel timing workloads')

    def test_sample_missing(self):
        self.reject(audit.inspect_samples,('report','workloads',0,'samples'),lambda r:r.pop(),'all five interleaved original timing pairs')

    def test_pair_order_changed(self):
        self.reject(audit.inspect_samples,('report','workloads',0,'samples'),lambda r:r.reverse(),'all five interleaved original timing pairs')

    def test_spacing_flag_removed(self):
        self.reject(audit.inspect_samples,('report','workloads',6,'samples',0,'command'),lambda r:r.pop(),'exact actual full novel timing command')

    def test_unannotated_mislabeled_as_raw(self):
        self.reject(audit.inspect_samples,('report','workloads',0,'samples',0,'command'),lambda r:r.extend(['--dictionary','invented']),'exact actual full novel timing command')

    def test_nonfinite_timing(self):
        self.reject(audit.inspect_samples,('report','workloads',0,'samples',0),lambda r:r.update(seconds=float('nan')),'finite original timing measurements')

    def test_summary_forged(self):
        self.reject(audit.inspect_samples,('report','workloads',0,'summary','after'),lambda r:r.update(median_seconds=0),'independently recomputed every original timing summary')

    def test_parity_policy_missing(self):
        self.reject(audit.inspect_parity,('report','cache_parity'),lambda r:r.pop(),'all three original cache parity policies')

    def test_cache_size_missing(self):
        self.reject(audit.inspect_parity,('report','cache_parity',0,'checks'),lambda r:r.pop(),'both complete original cache sizes')

    def test_wrong_parity_output(self):
        self.reject(audit.inspect_parity,('report','cache_parity',0,'checks',0),lambda r:r.update(sha256='changed'),'all179112 cache parity records')

    def test_parity_truncated(self):
        self.reject(audit.inspect_parity,('report','cache_parity',0,'checks',0),lambda r:r.update(records=179111),'all179112 cache parity records')


    def test_archived_inputs_false_live_claim(self):
        self.reject(audit.inspect_evidence,('original_input_evidence',),lambda r:r.update(live_non_executable_files_verified=True),'honest original timing input evidence scope')

    def test_archived_original_payload_missing(self):
        self.reject(audit.inspect_evidence,('originals',),lambda r:r.pop(next(iter(r))),'all22 complete timing and failure artifacts')

    def test_archive_catalog_changed(self):
        self.reject(audit.inspect_evidence,('manifest','files','friendly-command-gena-performance.json'),lambda r:r.update(source_sha256='invented'),'immutable original timing archive catalog')

    def test_archived_original_payload_changed(self):
        self.reject(audit.inspect_evidence,('originals',),lambda r:r.__setitem__('friendly-command-gena-performance.json',b'{}'),'every immutable original timing artifact body')

    def test_original_preflight_failure_reclassified(self):
        self.reject(audit.inspect_evidence,('values','first-failed-friendly-command-gena-performance-audit-validation.json'),lambda r:r.update(state='passed'),'original missing-executable preflight stays failed')

    def test_original_control_failure_hidden(self):
        self.reject(audit.inspect_evidence,('values','friendly-command-gena-performance-audit-validation-retry1.json'),lambda r:r.update(errors=1),'actual original23 captured performance controls')


if __name__ == '__main__':
    unittest.main()
