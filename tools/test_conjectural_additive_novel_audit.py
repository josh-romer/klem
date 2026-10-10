"""Mutations must fail even when the affected observation hash is repaired."""
import copy
import json
import unittest
import conjectural_additive_novel_audit as audit

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.values = audit.inputs()

    def reject(self, mutate, message):
        values = copy.deepcopy(self.values)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, message): audit.inspect(values)

    def edit_stream(self, values, mutate):
        run = values['capture']['runs'][0]
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        mutate(run, rows)
        run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows)
        run['jsonl_sha256'] = audit.sha(run['jsonl'].encode())
        values['capture']['commands'][30]['stdout_sha256'] = run['jsonl_sha256']

    def test_complete_actual_capture(self):
        self.assertEqual(audit.inspect(self.values)['typed_occurrence_checks'], 384)

    def test_original_line_truncated(self):
        self.reject(lambda v: v['author']['items'][0].update(complete_original_line='하려니와'), 'complete original line retained')

    def test_original_span_shifted(self):
        self.reject(lambda v: v['author']['items'][0]['span'].update(start=759), 'exact original target spans')

    def test_occurrence_erased(self):
        self.reject(lambda v: v['author']['items'].pop(), 'all fifteen literal original occurrences')

    def test_target_rewritten_to_output(self):
        def mutate(v):
            suite = json.loads(v['fixture_raw']); suite['cases'][11]['judgments'][0]['lemmas'] = ['나', '이다']
            v['fixture_raw'] = json.dumps(suite, ensure_ascii=False).encode()
        self.reject(mutate, 'independent novel targets unchanged')

    def test_native_projection_pos_fabricated(self):
        def mutate(v):
            entries = json.loads(v['native_entries_raw']); entries['krdict:36428']['pos'] = '명사'
            v['native_entries_raw'] = json.dumps(entries, ensure_ascii=False).encode()
        self.reject(mutate, 'complete Native projections unchanged')

    def test_original_export_snapshot_changed(self):
        self.reject(lambda v: v['closure']['original_exports'][next(iter(v['closure']['original_exports']))].update(sha256='0' * 64), 'all eleven original exports bound')

    def test_failed_cli_entry_hidden(self):
        self.reject(lambda v: v['capture']['commands'][1].update(exit_code=1), 'all actual import/entry/stream commands succeeded')

    def test_unicode_policy_stream_duplicated(self):
        self.reject(lambda v: v['capture']['runs'][1].update(cache_bytes=0), 'complete twenty-four policy/Unicode/cache streams')

    def test_compatible_command_replaced(self):
        self.reject(lambda v: v['capture']['runs'][4]['command'].remove('--dict-compatible'), 'actual correct filter/cache command')

    def test_frame_erased_with_output_hash_repaired(self):
        self.reject(lambda v: self.edit_stream(v, lambda run, rows: rows.pop()), 'all complete output frames')

    def test_typed_path_role_changed_with_output_hash_repaired(self):
        def mutate(run, rows):
            observation = run['observations'][2]
            row = rows[observation['record_index']]
            for path in row['analysis']['analyses']:
                if [lemma['text'] for lemma in path['lemmas']] == ['그만', '이다']:
                    path['lemmas'][0]['kind'] = 'nominal'
        self.reject(lambda v: self.edit_stream(v, mutate), 'every independently authored typed target recovered')

    def test_dictionary_owner_reassigned_with_output_hash_repaired(self):
        def mutate(run, rows):
            row = rows[run['observations'][2]['record_index']]
            lemma = next(lemma for lemma in row['dictionary']['lemmas'] if lemma['entries'])
            lemma['entries'][0]['headword'] = 'invented'
        self.reject(lambda v: self.edit_stream(v, mutate), 'real original Native lemma owner')

    def test_observation_indices_fabricated(self):
        self.reject(lambda v: v['capture']['runs'][0]['observations'][0]['judgments'][0]['typed_path_indices'].clear(), 'exact original independent target matches')

if __name__ == '__main__': unittest.main()
