"""Ensure the independent source review rejects changed originals and lost alternatives."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

import literary_future_kko_audit as audit
ORIGINAL = audit.inputs()

class SourceControls(unittest.TestCase):
    def rejected(self, mutate):
        args = copy.deepcopy(ORIGINAL); mutate(*args)
        with self.assertRaises((AssertionError, KeyError, ValueError, StopIteration)):
            audit.inspect(*args)

    def test_actual_complete_capture(self):
        self.assertEqual(audit.inspect(*ORIGINAL)['original_observations'], 114)

    def test_missing_complete_dialogue(self):
        self.rejected(lambda s,p,r: s['all_original_groups'].pop())

    def test_lost_source_note(self):
        self.rejected(lambda s,p,r: s['sqlite_entries']['krdict:81026']['senses'][1]['notes'].clear())

    def test_wrong_source_occurrence(self):
        self.rejected(lambda s,p,r: p['original_cases'][0]['source_occurrence'].update(line_index=2))

    def test_missing_mode(self):
        self.rejected(lambda s,p,r: r['runs'].pop())

    def test_missing_native_owner(self):
        self.rejected(lambda s,p,r: p['complete_native_entries'].pop(next(iter(p['complete_native_entries']))))

    def test_changed_english_projection(self):
        self.rejected(lambda s,p,r: p['english_projection']['LexicalResource']['Lexicon']['LexicalEntry'].pop())

    def test_changed_selected_parent(self):
        self.rejected(lambda s,p,r: p['original_cases'][0]['earlier_parent']['analysis']['lemmas'][0].update(text='먹다'))

    def test_changed_parent_native_assessment(self):
        self.rejected(lambda s,p,r: p['original_cases'][0]['earlier_parent']['assessment'].update(status='incompatible'))

    def test_changed_proposed_target(self):
        self.rejected(lambda s,p,r: p['original_cases'][0]['expected']['lemmas'].__setitem__(0,'먹다'))

    def test_missing_individual_source_observation(self):
        self.rejected(lambda s,p,r: r['original_targets'].pop())

    def test_missing_original_baseline_observation(self):
        self.rejected(lambda s,p,r: s['target_observations'].pop())

    def test_invented_judgment_for_other_candidate(self):
        self.rejected(lambda s,p,r: r['individual_additions'][0].update(structural_verdict='required'))

    def test_lost_matched_owner(self):
        self.rejected(lambda s,p,r: r['matched_native_owner_ids'].pop())

    def test_changed_unicode_span_even_with_fresh_stream_hash(self):
        def mutate(s,p,r):
            run = r['runs'][3]; rows = list(map(json.loads,run['jsonl'].splitlines()))
            rows[0]['span']['end'] += 1
            run['jsonl'] = ''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows)
            run['after_sha256'] = audit.sha(run['jsonl'].encode())
        self.rejected(mutate)

    def test_removed_old_path_even_with_fresh_stream_hash(self):
        def mutate(s,p,r):
            run = r['runs'][0]; rows = list(map(json.loads,run['jsonl'].splitlines()))
            row = next(row for row in rows if row.get('analysis') and len(row['analysis']['analyses']) > 1)
            row['analysis']['analyses'].pop(0); row['dictionary']['readings'].pop(0)
            run['jsonl'] = ''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows)
            run['after_sha256'] = audit.sha(run['jsonl'].encode())
        self.rejected(mutate)

if __name__ == '__main__': unittest.main()
