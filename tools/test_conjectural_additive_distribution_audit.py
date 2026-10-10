"""Require rejection of erased original gold, candidates, contexts and filters."""
import copy
import json
import unittest
from pathlib import Path

import conjectural_additive_distribution_audit as audit

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs(Path(__file__).resolve().parent)

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.values)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(values)

    def test_complete_actual_distributions(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['cohort_words'], result['annotated_rows'], result['broad_frames']), (53502, 66570, 1128312))

    def test_original_cohort_word_omitted(self):
        self.reject(lambda v: v['cohorts']['runs'][0]['captures'][0]['words'].pop(next(iter(v['cohorts']['runs'][0]['captures'][0]['words']))), 'all exact original cohort words')

    def test_new_cohort_candidate_erased(self):
        self.reject(lambda v: next(iter(v['cohorts']['runs'][0]['captures'][1]['words'].values()))['analyses'].pop(), 'all cohort outputs unchanged')

    def test_original_gold_altered(self):
        self.reject(lambda v: v['original_gold']['corpora'][0]['original_converted_rows'][0].update(expected=['invented']), 'all independent original annotation IDs/surfaces/gold')

    def test_annotated_row_omitted_with_hash_repaired(self):
        def mutate(v):
            run = v['gold']['runs'][0]
            run['jsonl'] = '\n'.join(run['jsonl'].splitlines()[:-1]) + '\n'
            run['stdout_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject(mutate, 'all annotated output and original recall unchanged')

    def test_gold_partition_omitted(self):
        self.reject(lambda v: v['gold']['runs'].pop(), 'all four complete annotated partitions')

    def test_original_installed_adapter_replaced(self):
        self.reject(lambda v: v['gold']['runs'][0]['before_command'].__setitem__(0, '/tmp/invented-adapter'), 'actual bound original adapter command')

    def test_broad_stream_omitted(self):
        self.reject(lambda v: v['broad']['runs'].pop(), 'all eight complete broad streams')

    def test_broad_compatible_flag_removed(self):
        self.reject(lambda v: v['broad']['runs'][5]['commands'][1].remove('--dict-compatible'), 'actual broad filter/spacing flags')

    def test_broad_spacing_flag_removed(self):
        self.reject(lambda v: v['broad']['runs'][6]['commands'][1].remove('--suggest-spacing'), 'actual broad filter/spacing flags')

    def test_novel_occurrence_omitted(self):
        self.reject(lambda v: v['broad']['runs'][3]['changed_frames'].pop(), 'every independently rederived original novel occurrence')

    def test_original_novel_context_clipped(self):
        self.reject(lambda v: v['broad']['runs'][3]['changed_frames'][0].update(complete_original_line='하려니와'), 'complete original novel context retained')

    def test_unjudged_novel_occurrence_promoted(self):
        self.reject(lambda v: v['broad']['runs'][3]['changed_frames'][0].update(contextual_verdict='required'), 'stable individually unjudged novel occurrence')

    def test_old_novel_candidate_erased(self):
        def mutate(v):
            item = v['broad']['runs'][3]['changed_frames'][0]
            item['after']['analysis']['analyses'].remove(item['before']['analysis']['analyses'][0])
        self.reject(mutate, 'every original novel candidate retained')

    def test_old_native_assessment_rewritten(self):
        def mutate(v):
            item = v['broad']['runs'][3]['changed_frames'][0]
            paths = item['after']['analysis']['analyses']
            index = paths.index(item['before']['analysis']['analyses'][0])
            item['after']['dictionary']['readings'][index]['status'] = 'tampered'
        self.reject(mutate, 'every original novel Native assessment retained')

    def test_new_novel_candidate_not_tracked(self):
        self.reject(lambda v: v['broad']['runs'][3]['changed_frames'][0]['new_paths'].pop(), 'every new novel candidate individually retained')

    def test_missing_new_novel_copula(self):
        def mutate(v):
            item = next(item for item in v['broad']['runs'][3]['changed_frames'] if item['after']['surface'] == '장래려니와')
            path = next(path for path in item['new_paths'] if 'copula.omitted_ending' in path['rules'])
            index = item['after']['analysis']['analyses'].index(path)
            item['after']['analysis']['analyses'].pop(index)
            item['after']['dictionary']['readings'].pop(index)
            item['new_paths'].remove(path)
        self.reject(mutate, 'original novel independently typed omitted copula present')

if __name__ == '__main__':
    unittest.main()
