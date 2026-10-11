"""Reject altered promoted package, judgment, runtime, stream, and browser evidence."""
import copy
import gzip
import re
import unittest

import friendly_command_gena_promoted_installed_audit as audit


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

    def test_complete_original_promoted_captures(self):
        result = audit.inspect(self.values)
        type(self).summary = result
        self.assertEqual((result['shared_cases'], result['scoped_reviews']), (35764, 520))
        self.assertEqual(result['annotated_gold_rows'], 66570)
        self.assertFalse(result['full_coverage_complete'])

    def test_wrong_promoted_checkpoint(self):
        self.reject(audit.inspect_packages, ('package',), lambda r: r.update(head='borrowed'), 'same actual promoted checkpoint')

    def test_failed_full_gate(self):
        self.reject(audit.inspect_packages, ('gate',), lambda r: r.update(state='failed'), 'actual terminal Gena scope')

    def test_missing_inventory_check(self):
        self.reject(audit.inspect_packages, ('gate', 'command'), lambda r: r.pop(), 'all four actual promoted checks')

    def test_missing_actual_build_result(self):
        self.reject(audit.inspect_packages, ('gate', 'results'), lambda r: r.pop(), 'all selected102 and complete Nix commands')

    def test_changed_selected_promotion_scope(self):
        self.reject(audit.inspect_packages, ('gate',), lambda r: r.update(promoted_cases=35740), 'actual full promoted ledger and review scope')

    def test_changed_selected_review_scope(self):
        self.reject(audit.inspect_packages, ('gate',), lambda r: r.update(scoped_reviews=519), 'actual full promoted ledger and review scope')

    def test_complete_judgment_binding_cannot_be_refreshed(self):
        values = self.values.copy()
        for name in ['gate', 'package']:
            values[name] = copy.copy(values[name])
            values[name]['frozen_inputs'] = copy.copy(values[name]['frozen_inputs'])
            values[name]['frozen_inputs']['tests/fixtures/validity.json'] = 'refreshed-invalid-judgments'
        values['gate']['inventory_source_files'] = copy.copy(values['gate']['inventory_source_files'])
        values['gate']['inventory_source_files']['tests/fixtures/validity.json'] = 'refreshed-invalid-judgments'
        with self.assertRaisesRegex(AssertionError, 'every original complete promoted fixture judgment and review byte'):
            audit.inspect_packages(values)

    def test_missing_packaged_launcher(self):
        self.reject(audit.inspect_packages, ('package', 'outputs'), lambda r: r.pop(), 'all actual promoted package outputs')

    def test_borrowed_full_gate_receipt(self):
        self.reject(audit.inspect_packages, ('package',), lambda r: r.update(complete_gate_sha256='borrowed'), 'complete original promoted gate prerequisite')

    def test_release_doctest_omitted(self):
        values = self.values.copy()
        values['release_log'] = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', values['release_log']).replace(b'Doc-tests klem', b'Not a documentation test')
        values['package'] = copy.copy(values['package'])
        values['package']['release_log_sha256'] = audit.sha(values['release_log'])
        with self.assertRaisesRegex(AssertionError, 'original release documentation test retained'):
            audit.inspect_packages(values)

    def test_compiled_json_input_omitted(self):
        self.reject(audit.inspect_packages, ('installed', 'profiles', 'klem', 'files'), lambda r: r.pop('src/dictionary/proper_names.json'), 'complete selected installed promoted profile equality')

    def test_current_installed_executable_replaced(self):
        self.reject(audit.inspect_packages, ('installed', 'binaries', 'klem'), lambda r: r.update(sha256='changed'), 'exact actual promoted executable')

    def test_parent_debug_executable_unprotected(self):
        path = next(iter(self.values['gate']['protected_binaries']))
        self.reject(audit.inspect_packages, ('installed', 'frozen_inputs'), lambda r: r.__setitem__(path, 'changed'), 'all six original protected executables')

    def test_cli_policy_missing(self):
        self.reject(audit.inspect_runtime, ('installed', 'source_runs'), lambda r: r.pop(), 'all36 complete installed policies')

    def test_complete_native_owner_missing(self):
        self.reject(audit.inspect_runtime, ('installed', 'native_records'), lambda r: r.pop(), 'all44 complete installed Native owners')

    def test_headword_lookup_missing(self):
        self.reject(audit.inspect_runtime, ('installed', 'lookup_records'), lambda r: r.pop(), 'all69 installed new lemma lookups')

    def test_cohort_old_candidate_order_changed(self):
        words = self.values['installed']['cohort_runs'][0]['words']
        surface = next(s for s, word in words.items() if len(word['analyses']) > 1)
        self.reject(audit.inspect_runtime, ('installed', 'cohort_runs', 0, 'words', surface, 'analyses'), lambda r: r.reverse(), 'every original ordered installed WordAnalysis')

    def test_gold_partition_missing(self):
        self.reject(audit.inspect_runtime, ('installed', 'corpus_runs'), lambda r: r.pop(), 'all four installed gold partitions')

    def test_broad_policy_missing(self):
        self.reject(audit.inspect_runtime, ('installed', 'broad_runs'), lambda r: r.pop(), 'all eight installed broad streams')

    def test_broad_context_replaced(self):
        self.reject(audit.inspect_runtime, ('installed', 'broad_runs', 0, 'changed_frames'), lambda r: r.append({'invented': 'context'}), 'all18 full original unjudged broad contexts and paths')

    def test_explicit_command_stream_missing(self):
        self.reject(audit.inspect_runtime, ('installed', 'command_attempts'), lambda r: r.pop(), 'all161 explicit policy Native gold and broad commands retained')

    def test_actual_input_replaced(self):
        self.reject(audit.inspect_runtime, ('installed', 'command_attempts', 0), lambda r: r.update(input='different'), 'complete explicit capture command and original input order')

    def test_packed_actual_stream_changed(self):
        path = self.values['installed']['command_attempts'][0]['streams']['stdout']['path']
        self.reject(audit.inspect_runtime, ('command_streams',), lambda r: r.__setitem__(path, b'changed'), 'actual retained packed stream bytes')

    def test_forged_output_cannot_borrow_original_rows(self):
        values = self.values.copy(); values['installed'] = copy.copy(values['installed'])
        values['installed']['command_attempts'] = list(values['installed']['command_attempts'])
        attempt = copy.deepcopy(values['installed']['command_attempts'][0])
        values['installed']['command_attempts'][0] = attempt
        raw = b'forged output\n'; packed = gzip.compress(raw, mtime=0)
        stream = attempt['streams']['stdout']; path = stream['path']
        stream.update(source_sha256=audit.sha(raw), archive_sha256=audit.sha(packed), bytes=len(raw))
        values['installed']['frozen_inputs'] = copy.copy(values['installed']['frozen_inputs'])
        values['installed']['frozen_inputs'][path] = audit.sha(packed)
        values['command_streams'] = copy.copy(values['command_streams']); values['command_streams'][path] = packed
        with self.assertRaisesRegex(AssertionError, 'actual complete output bound to independently verified record'):
            audit.inspect_runtime(values)

    def test_browser_server_not_stopped(self):
        self.reject(audit.inspect_browser, ('browser_runtime',), lambda r: r.update(server_stopped=False), 'owned installed browser source freeze/shutdown')

    def test_browser_uses_borrowed_launcher(self):
        self.reject(audit.inspect_browser, ('browser_runtime', 'command'), lambda r: r.__setitem__(0, 'borrowed'), 'actual packaged launcher browser command')

    def test_browser_original_native_owner_missing(self):
        self.reject(audit.inspect_browser, ('browser', 'nativeEntries'), lambda r: r.pop(), 'every independently audited original installed browser choice/form/Native/export')

    def test_browser_component_order_changed(self):
        self.reject(audit.inspect_browser, ('browser', 'diagrams', 0, 'forms'), lambda r: r.reverse(), 'every independently audited original installed browser choice/form/Native/export')

    def test_browser_original_selector_option_missing(self):
        self.reject(audit.inspect_browser, ('browser', 'policyDecisions', 0, 'offered_indices'), lambda r: r.pop(), 'every independently audited original installed browser choice/form/Native/export')

    def test_browser_current_source_snapshot_omitted(self):
        self.reject(audit.inspect_browser, ('browser_runtime', 'source_inputs'), lambda r: r.pop(next(iter(r))), 'same complete installed browser checkpoint')

    def test_actual_served_asset_replaced(self):
        self.reject(audit.inspect_browser, ('browser_runtime', 'served_assets', 0), lambda r: r.update(sha256='changed'), 'actual installed served assets')

    def test_retained_screenshot_omitted(self):
        self.reject(audit.inspect_browser, ('browser_runtime', 'screenshots'), lambda r: r.pop('mobile'), 'both actual promoted screenshots retained')

    def test_original_failed_recorder_artifact_missing(self):
        values = self.values.copy()
        manifest = audit.json.loads(values['failed_prefix_manifest_raw'])
        manifest['files'].pop(next(iter(manifest['files'])))
        values['failed_prefix_manifest_raw'] = audit.json.dumps(manifest).encode()
        with self.assertRaisesRegex(AssertionError, 'all313 original failed recorder artifacts retained'):
            audit.streams.inspect_prefix(values)

    def test_original_failed_recorder_bytes_changed(self):
        name = next(iter(self.values['failed_prefix_originals']))
        self.reject(audit.streams.inspect_prefix, ('failed_prefix_originals',), lambda r: r.__setitem__(name, b'changed'), 'complete original failed recorder packed artifact')

    def test_failed_recorder_cannot_be_promoted_to_passed(self):
        values = self.values.copy()
        name = 'friendly-command-gena-promoted-installed-runtime.json.gz'
        seed = audit.json.loads(gzip.decompress(gzip.decompress(values['failed_prefix_originals'][name])))
        seed['state'] = 'passed'
        raw = gzip.compress(audit.json.dumps(seed).encode(), mtime=0)
        packed = gzip.compress(raw, mtime=0)
        manifest = audit.json.loads(values['failed_prefix_manifest_raw'])
        manifest['files'][name].update(source_sha256=audit.sha(raw), archive_sha256=audit.sha(packed), bytes=len(raw))
        values['failed_prefix_manifest_raw'] = audit.json.dumps(manifest).encode()
        values['failed_prefix_originals'] = dict(values['failed_prefix_originals'], **{name: packed})
        with self.assertRaisesRegex(AssertionError, 'original recorder receipt remains failed'):
            audit.streams.inspect_prefix(values)

    def test_failed_partial_cohort_limits_cannot_be_hidden(self):
        values = self.values.copy()
        manifest = audit.json.loads(values['failed_prefix_manifest_raw'])
        manifest['unrecorded_concurrent_bytes_may_be_missing'] = False
        values['failed_prefix_manifest_raw'] = audit.json.dumps(manifest).encode()
        with self.assertRaisesRegex(AssertionError, 'failed concurrent recorder limits retained'):
            audit.streams.inspect_prefix(values)

    def test_reused_prefix_checkpoint_changed(self):
        self.reject(audit.streams.inspect_prefix, ('installed',), lambda r: r.update(captured_head='different'), 'same source and package checkpoint for reused prefix')

    def test_reused_prefix_cannot_be_claimed_as_fresh_commands(self):
        self.reject(audit.streams.inspect_prefix, ('installed', 'reused_completed_prefix'), lambda r: r.update(prefix_commands_replayed=149), 'exact failed prefix reuse provenance')

    def test_original_prefix_command_order_retained(self):
        self.reject(audit.streams.inspect_prefix, ('installed', 'command_attempts'), lambda r: r.reverse(), 'actual149 commands reused in original order')

    def test_cohort_command_missing(self):
        self.reject(audit.streams.inspect_cohorts, ('installed', 'cohort_command_attempts'), lambda r: r.pop(), 'all75 actual cohort commands and two complete cohorts')

    def test_cohort_stream_missing(self):
        self.reject(audit.streams.inspect_cohorts, ('cohort_command_streams',), lambda r: r.pop(next(iter(r))), 'all150 whole actual cohort streams retained')

    def test_cohort_stream_bytes_changed(self):
        path = self.values['installed']['cohort_command_attempts'][0]['streams']['stdout']['path']
        self.reject(audit.streams.inspect_cohorts, ('cohort_command_streams',), lambda r: r.__setitem__(path, b'changed'), 'actual packed cohort stream binding')

    def test_cohort_actual_input_hash_changed(self):
        self.reject(audit.streams.inspect_cohorts, ('installed', 'cohort_command_attempts', 0), lambda r: r.update(input_sha256='changed'), 'actual cohort input hash')

    def test_cohort_actual_executable_changed(self):
        self.reject(audit.streams.inspect_cohorts, ('installed', 'cohort_command_attempts', 0, 'command'), lambda r: r.__setitem__(0, 'borrowed'), 'actual complete cohort command and input')

    def test_cohort_forged_span_with_coordinated_hashes_rejected(self):
        values = self.values.copy()
        values['installed'] = copy.copy(values['installed'])
        values['installed']['cohort_command_attempts'] = list(values['installed']['cohort_command_attempts'])
        attempt = copy.deepcopy(values['installed']['cohort_command_attempts'][0])
        values['installed']['cohort_command_attempts'][0] = attempt
        stream = attempt['streams']['stdout']; path = stream['path']
        lines = gzip.decompress(values['cohort_command_streams'][path]).splitlines()
        frame = audit.json.loads(lines[0]); frame['span']['start'] += 1
        lines[0] = audit.json.dumps(frame, ensure_ascii=False).encode()
        raw = b'\n'.join(lines) + b'\n'; packed = gzip.compress(raw, mtime=0)
        stream.update(source_sha256=audit.sha(raw), archive_sha256=audit.sha(packed), bytes=len(raw))
        values['cohort_command_streams'] = dict(values['cohort_command_streams'], **{path: packed})
        values['installed']['frozen_inputs'] = dict(values['installed']['frozen_inputs'], **{path: audit.sha(packed)})
        with self.assertRaisesRegex(AssertionError, 'complete original cohort UTF8 frame spans'):
            audit.streams.inspect_cohorts(values)


if __name__ == '__main__': unittest.main()
