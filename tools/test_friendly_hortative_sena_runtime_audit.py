"""Reject altered Sena output even when its local stdout is regenerated."""
import copy
import json
import unittest

import friendly_hortative_sena_runtime_audit as audit


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

    def binding(self, path, change, reason):
        self.reject(audit.inspect_binding, path, change, reason)

    def streams(self, path, change, reason):
        self.reject(audit.inspect_streams, path, change, reason)

    @staticmethod
    def stdout(run):
        run['stdout'] = ''.join(json.dumps(f, ensure_ascii=False) + '\n' for f in run['frames'])

    def test_complete_original_scope(self):
        result = audit.inspect(self.original)
        self.assertEqual((result['cli_runs'], result['old_path_occurrences'], result['required_checks']), (36, 2916, 324))
        self.assertFalse(result['full_coverage_complete'])

    def test_unknown_current_production_edit(self):
        self.binding(('current',), lambda r: r.update({'src/lib.rs': 'changed'}), 'complete44 current')

    def test_compiled_json_cannot_be_omitted(self):
        self.binding(('current',), lambda r: r.pop('src/dictionary/proper_names.json'), 'complete44 current')

    def test_frontend_public_asset_cannot_be_omitted(self):
        self.binding(('frontend',), lambda r: r.pop('web/public/favicon.svg'), 'complete18 current')

    def test_parent_source_cannot_be_borrowed(self):
        self.binding(('binding', 'parent_production_inputs'), lambda r: r.update({'src/lib.rs': 'changed'}), 'exact five declared')

    def test_declared_changes_cannot_be_expanded(self):
        self.binding(('binding', 'declared_production_changes'), lambda r: r.append('src/lib.rs'), 'exact five declared')

    def test_compile_profile_cannot_drop_native_fixture(self):
        self.binding(('binding', 'compiled_profiles', 'klem', 'files'), lambda r: r.pop('tests/fixtures/friendly-hortative-sena-native.json'), 'all actual selected compile')

    def test_frozen_compile_input_cannot_change(self):
        self.binding(('binding', 'frozen_inputs'), lambda r: r.update({'Cargo.lock': 'changed'}), 'every captured compile')

    def test_source_index_freeze_cannot_be_hidden(self):
        self.binding(('binding',), lambda r: r.update(index_unchanged=False), 'captured Source/HEAD/index')

    def test_original_parent_binary_freeze_cannot_be_hidden(self):
        self.binding(('binding',), lambda r: r.update(protected_parent_binaries_unchanged=False), 'protected parent inputs')

    def test_selected_control_count_cannot_be_invented(self):
        self.binding(('selected',), lambda r: r.update(controls=65), 'actual selected64')

    def test_selected_failed_command_cannot_be_hidden(self):
        self.binding(('selected', 'results', 1), lambda r: r.update(exit_code=1), 'all selected commands')

    def test_build_command_cannot_omit_adapter(self):
        self.binding(('binding', 'results', 0, 'command'), lambda r: r.pop(), 'actual CLI/server/adapter build')

    def test_build_log_binding_cannot_change(self):
        self.binding(('binding',), lambda r: r.update(log_sha256='changed'), 'full original build log')

    def test_binary_set_cannot_omit_server(self):
        self.binding(('binding', 'binaries'), lambda r: r.pop('server'), 'all three captured binaries')

    def test_server_binary_fingerprint_cannot_change(self):
        self.binding(('current_binaries',), lambda r: r.update(server='changed'), 'all actual current binary fingerprints')

    def test_cli_executable_binding_cannot_change(self):
        cli = self.original['binding']['binaries']['klem']['path']
        self.streams(('streams', 'external_inputs'), lambda r: r.update({cli: 'changed'}), 'exact captured CLI')

    def test_runtime_source_revision_cannot_change(self):
        self.streams(('streams',), lambda r: r.update(head='changed'), 'same current binary Source')

    def test_runtime_source_snapshot_cannot_drop_file(self):
        self.streams(('streams', 'frozen_inputs'), lambda r: r.pop('Cargo.lock'), 'same complete7049')

    def test_failed_runtime_receipt_cannot_be_hidden(self):
        self.streams(('streams',), lambda r: r.update(state='failed'), 'actual passed terminal')

    def test_runtime_log_binding_cannot_change(self):
        self.streams(('streams',), lambda r: r.update(log_sha256='changed'), 'full original runtime log')

    def test_unicode_filter_cache_policy_cannot_be_omitted(self):
        self.streams(('captures', 'captures'), lambda r: r.pop(), 'every36 policy')

    def test_original_dialogue_input_cannot_be_trimmed(self):
        self.streams(('captures', 'captures', 0), lambda r: r.update(input='하세나'), 'entire baseline input')

    def test_filter_command_cannot_change(self):
        self.streams(('captures', 'captures', 0, 'command'), lambda r: r.append('--dict-only'), 'actual bound Unicode/filter/cache')

    def test_nonzero_execution_cannot_be_hidden(self):
        self.streams(('captures', 'captures', 0), lambda r: r.update(exit_code=1), 'actual bound Unicode/filter/cache')

    def test_byte_span_cannot_change_with_refreshed_stdout(self):
        def change(run):
            run['frames'][0]['span']['start'] += 1
            self.stdout(run)
        self.streams(('captures', 'captures', 0), change, 'contiguous Unicode byte spans')

    def test_old_candidate_cannot_be_removed_with_refreshed_stdout(self):
        def change(run):
            next(f for f in run['frames'] if f['kind'] == 'word')['analysis']['analyses'].pop(0)
            self.stdout(run)
        self.streams(('captures', 'captures', 0), change, 'every old candidate and relative order')

    def test_old_candidate_order_cannot_change_with_refreshed_stdout(self):
        def change(run):
            next(f for f in run['frames'] if f['kind'] == 'word' and len(f['analysis']['analyses']) > 1)['analysis']['analyses'].reverse()
            self.stdout(run)
        self.streams(('captures', 'captures', 0), change, 'every old candidate and relative order')

    def test_dictionary_fingerprint_cannot_change_with_refreshed_stdout(self):
        def change(run):
            next(f for f in run['frames'] if f['kind'] == 'word')['dictionary']['fingerprint'] = 'changed'
            self.stdout(run)
        self.streams(('captures', 'captures', 0), change, 'original dictionary source and fingerprint')

    def test_old_assessment_cannot_change_with_refreshed_stdout(self):
        def change(run):
            next(f for f in run['frames'] if f['kind'] == 'word')['dictionary']['readings'][0]['status'] = 'changed'
            self.stdout(run)
        self.streams(('captures', 'captures', 0), change, 'every old full dictionary assessment')

    def test_new_path_cannot_borrow_se_plus_na(self):
        def change(run):
            frame = next(f for f in run['frames'] if f['kind'] == 'word' and any(audit.RULE in p['rules'] for p in f['analysis']['analyses']))
            path = next(p for p in frame['analysis']['analyses'] if audit.RULE in p['rules'])
            path['morphemes'] = [{'form': '세', 'kind': 'ending'}, {'form': '나', 'kind': 'particle'}]
            self.stdout(run)
        self.streams(('captures', 'captures', 0), change, 'only canonical Sena additions')

    def test_added_path_assessment_record_cannot_be_omitted(self):
        self.streams(('captures', 'captures', 0, 'new_paths'), lambda r: r.pop(), 'all rederived added paths')

    def test_observation_cannot_borrow_other_case_id(self):
        self.streams(('captures', 'captures', 0, 'observations', 0), lambda r: r.update(case_id='borrowed'), 'all rederived judgment')

    def test_summary_cannot_hide_required_path_count(self):
        self.streams(('streams',), lambda r: r.update(required_checks=323), 'reported totals equal')

    def test_summary_cannot_claim_fewer_new_hypotheses(self):
        self.streams(('streams',), lambda r: r.update(new_unjudged_paths=715), 'reported totals equal')

    def test_complete_native_owner_cannot_be_omitted(self):
        self.streams(('captures', 'native_entries'), lambda r: r.pop('krdict:78469'), 'all36 complete Native')

    def test_full_native_definition_cannot_change(self):
        self.streams(('captures', 'native_entries', 'krdict:78469', 'response', 'entry'), lambda r: r.update(notes=['invented']), 'complete original Native fields')

    def test_full_native_stdout_cannot_change_even_when_response_agrees(self):
        def change(row):
            row['response']['entry']['notes'] = ['invented']
            row['stdout'] = json.dumps(row['response'], ensure_ascii=False) + '\n'
        self.streams(('captures', 'native_entries', 'krdict:78469'), change, 'unchanged full Native stdout')

    def test_unknown_prefinal_cannot_claim_compatible_status(self):
        run = next(i for i, r in enumerate(self.original['captures']['captures']) if r['family'] == 'unjudged-lexical-prefinal-boundaries' and r['mode'] == 'all' and r['normalization'] == 'NFC' and r['cache_bytes'] == 0)
        def change(r):
            frame = next(f for f in r['frames'] if f['surface'] == '먹었세나')
            i = next(i for i, p in enumerate(frame['analysis']['analyses']) if [l['text'] for l in p['lemmas']] == ['먹다'] and [m['form'] for m in p['morphemes']] == ['었', '세나'] and audit.RULE in p['rules'])
            frame['dictionary']['readings'][i]['status'] = 'compatible'
        self.reject(audit.inspect_boundaries, ('captures', 'captures', run), change, 'unreviewed prefinals keep Unknown')

    def test_bare_adjective_cannot_borrow_verb_status(self):
        run = next(i for i, r in enumerate(self.original['captures']['captures']) if r['family'] == 'unjudged-lexical-prefinal-boundaries' and r['mode'] == 'all' and r['normalization'] == 'NFC' and r['cache_bytes'] == 0)
        def change(r):
            frame = next(f for f in r['frames'] if f['surface'] == '예쁘세나')
            i = next(i for i, p in enumerate(frame['analysis']['analyses']) if [l['text'] for l in p['lemmas']] == ['예쁘다'] and [m['form'] for m in p['morphemes']] == ['세나'] and audit.RULE in p['rules'])
            frame['dictionary']['readings'][i]['status'] = 'compatible'
        self.reject(audit.inspect_boundaries, ('captures', 'captures', run), change, 'bare known adjective cannot borrow')

    def test_rieul_recovery_cannot_be_invented_for_sada(self):
        run = next(i for i, r in enumerate(self.original['captures']['captures']) if r['family'] == 'preauthored-25-proposals' and r['mode'] == 'compatible' and r['normalization'] == 'NFC' and r['cache_bytes'] == 0)
        def change(r):
            frame = next(f for f in r['frames'] if f['surface'] == '사세나')
            path = next(p for p in frame['analysis']['analyses'] if [l['text'] for l in p['lemmas']] == ['사다'] and [m['form'] for m in p['morphemes']] == ['세나'] and audit.RULE in p['rules'])
            path['rules'].append('deletion.rieul')
        self.reject(audit.inspect_boundaries, ('captures', 'captures', run), change, 'both original lexical paths')


if __name__ == '__main__':
    unittest.main()
