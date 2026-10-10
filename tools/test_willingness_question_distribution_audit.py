"""Reject erased alternatives, rewritten annotations and unsupported precision claims."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import willingness_question_distribution_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = audit.inputs()

    def reject(self, function, obj, updates, reason):
        with patch.dict(obj, updates):
            with self.assertRaisesRegex(AssertionError, reason):
                function(self.v)

    def test_complete_original_distribution(self):
        result = audit.inspect(self.v)
        self.assertEqual((result['source_frames'], result['annotated_rows'], result['broad_frames']), (3336, 66570, 1128312))
        self.assertEqual((result['original_corpus_occurrences'], result['new_raw_annotated_candidates']), (14, 28))
        self.assertFalse(result['contextual_review_complete'])
        self.assertFalse(result['full_coverage_complete'])

    def test_original_archive_cannot_be_refreshed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'docs').mkdir()
            name = audit.PARENTS['cohorts'][0]
            (root / 'docs' / name).write_bytes(gzip.compress(b'{}', mtime=0))
            with patch.object(audit, 'ROOT', root):
                with self.assertRaisesRegex(AssertionError, 'unchanged original parent archive'):
                    audit.inputs()

    def test_nonterminal_capture(self):
        self.reject(audit.inspect_streams, self.v['streams'], {'state': 'running'}, 'terminal complete distribution capture')

    def test_changed_capture_inputs(self):
        self.reject(audit.inspect_broad, self.v['broad'], {'inputs_unchanged': False}, 'terminal complete distribution capture')

    def test_missing_source_cache_policy(self):
        report = self.v['streams']
        self.reject(audit.inspect_streams, report, {'runs': report['runs'][:-1]}, 'all original source policies')

    def test_source_filter_command(self):
        run = next(r for r in self.v['streams']['runs'] if r['mode'] == 'headword')
        self.reject(audit.inspect_streams, run, {'command': [arg for arg in run['command'] if arg != '--dict-only']}, 'actual source filter command')

    def test_erased_source_observation(self):
        run = self.v['streams']['runs'][0]
        self.reject(audit.inspect_streams, run, {'observations': run['observations'][:-1]}, 'all ending and expression observations')

    def test_expression_not_promoted_to_ending(self):
        observation = self.v['streams']['runs'][0]['observations'][10]
        self.reject(audit.inspect_streams, observation, {'morphological_judgment': 'required offer ending'}, 'expression semantics remain separate')

    def test_missing_original_cohort_word(self):
        run = self.v['cohorts']['runs'][0]
        words = run['captures'][1]['words']
        self.reject(audit.inspect_cohorts, run['captures'][1], {'words': {k: v for k, v in words.items() if k != '구소련'}}, 'every original cohort word retained')

    def test_erased_original_alternative(self):
        word = self.v['cohorts']['runs'][0]['captures'][1]['words']['구소련']
        self.reject(audit.inspect_cohorts, word, {'analyses': word['analyses'][1:]}, 'every ordered original candidate retained')

    def test_unrelated_new_rule(self):
        word = self.v['cohorts']['runs'][0]['captures'][1]['words']['구소련']
        path = next(p for p in word['analyses'] if 'ending.willingness_question' in p['rules'])
        self.reject(audit.inspect_cohorts, path, {'rules': ['fabricated']}, 'only new canonical willingness paths')

    def test_missing_individual_cohort_record(self):
        report = self.v['cohorts']
        self.reject(audit.inspect_cohorts, report, {'individual_changed_words': report['individual_changed_words'][:-1]}, 'every complete individual cohort observation')

    def test_contextual_cohort_verdict_not_inferred(self):
        observation = self.v['cohorts']['individual_changed_words'][0]
        self.reject(audit.inspect_cohorts, observation, {'contextual_verdict': 'forbidden'}, 'every complete individual cohort observation')

    def test_missing_complete_corpus_input(self):
        report = self.v['original_corpora']
        self.reject(audit.inspect_contexts, report, {'sources': dict(list(report['sources'].items())[:-1])}, 'all four complete original corpus inputs')

    def test_original_annotation_input_cannot_change(self):
        source = next(iter(self.v['original_corpora']['sources'].values()))
        self.reject(audit.inspect_contexts, source, {'text': source['text'] + '\n'}, 'unchanged complete original annotated input bytes')

    def test_missing_original_occurrence(self):
        contexts = self.v['contexts']
        self.reject(audit.inspect_contexts, contexts, {'corpus_occurrences': contexts['corpus_occurrences'][:-1]}, 'every independently derived complete annotated context')

    def test_cropped_original_sentence(self):
        occurrence = self.v['contexts']['corpus_occurrences'][0]
        self.reject(audit.inspect_contexts, occurrence, {'complete_original_sentence': occurrence['surface']}, 'every independently derived complete annotated context')

    def test_annotation_not_replaced_by_new_hypothesis(self):
        occurrence = self.v['contexts']['corpus_occurrences'][0]
        fields = list(occurrence['original_annotation_fields'])
        fields[2] = 'invented lemma'
        self.reject(audit.inspect_contexts, occurrence, {'original_annotation_fields': fields}, 'every independently derived complete annotated context')

    def test_missing_annotated_partition(self):
        gold = self.v['gold']
        self.reject(audit.inspect_gold, gold, {'runs': gold['runs'][:-1]}, 'all complete original annotated partitions')

    def test_corpus_output_cannot_be_refreshed(self):
        run = self.v['gold']['runs'][0]
        self.reject(audit.inspect_gold, run, {'jsonl': '{}\n'}, 'complete actual corpus output identity')

    def test_candidate_increase_cannot_be_hidden(self):
        run = self.v['gold']['runs'][0]
        self.reject(audit.inspect_gold, run, {'summary_changes': {}}, 'all exact corpus summary deltas retained')

    def test_fabricated_mean_with_consistent_output_digest(self):
        run = self.v['gold']['runs'][0]
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        rows[0]['mean_candidates'] += 1
        output = '\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n'
        self.reject(audit.inspect_gold, run, {'jsonl': output, 'stdout_sha256': audit.sha(output.encode())}, 'candidate mean independently explained by original contexts')

    def test_fabricated_gold_with_consistent_output_digest(self):
        run = self.v['gold']['runs'][0]
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        rows[1]['expected'] = [['invented']]
        output = '\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\n'
        self.reject(audit.inspect_gold, run, {'jsonl': output, 'stdout_sha256': audit.sha(output.encode())}, 'every original annotated row and recovery unchanged')

    def test_wrong_adapter_binary(self):
        run = self.v['gold']['runs'][0]
        self.reject(audit.inspect_gold, run, {'command': ['fabricated', *run['command'][1:]]}, 'actual bound corpus adapter commands')

    def test_missing_broad_stream(self):
        broad = self.v['broad']
        self.reject(audit.inspect_broad, broad, {'runs': broad['runs'][:-1]}, 'all eight complete broad streams')

    def test_parent_broad_output_cannot_be_refreshed(self):
        self.reject(audit.inspect_broad, self.v['broad']['runs'][0], {'before_jsonl_sha256': '0' * 64}, 'unchanged original broad baseline')

    def test_spacing_flag_cannot_disappear(self):
        run = self.v['broad']['runs'][-1]
        self.reject(audit.inspect_broad, run, {'commands': [c[:-1] for c in run['commands']]}, 'actual broad filter and spacing commands')

    def test_novel_context_cannot_be_cropped(self):
        item = self.v['broad']['runs'][3]['changed_frames'][0]
        self.reject(audit.inspect_broad, item, {'complete_original_line': '궐련'}, 'complete original novel passage bytes')

    def test_novel_hypothesis_not_automatically_forbidden(self):
        item = self.v['broad']['runs'][3]['changed_frames'][0]
        self.reject(audit.inspect_broad, item, {'contextual_verdict': 'forbidden'}, 'novel hypothesis is contextually unjudged')

    def test_missing_novel_context_observation(self):
        self.reject(audit.inspect_contexts, self.v['contexts'], {'complete_novel_observation': {}}, 'complete original novel observation')


if __name__ == '__main__':
    unittest.main()
