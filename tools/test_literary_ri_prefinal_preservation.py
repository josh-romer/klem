"""Reject lost candidates, altered owners, false judgments, and adapter drift."""
import copy
import json
import unittest

import literary_ri_prefinal_preservation as a


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.broad, cls.owners, cls.corpora, cls.adapter, cls.history = a.inputs()

    def reject_change(self, mapping, key, replacement, verify):
        original = mapping[key]
        mapping[key] = replacement
        try:
            with self.assertRaises((AssertionError, KeyError, ValueError, StopIteration)):
                verify()
        finally:
            mapping[key] = original

    def broad_check(self):
        return a.verify_broad(self.broad, self.owners)

    def corpus_check(self):
        return a.verify_corpora(self.corpora, self.adapter)

    def test_complete_captures(self):
        result = a.verify(self.broad, self.owners, self.corpora, self.adapter, self.history)
        self.assertEqual(result['corpora']['converted_rows'], 66570)
        self.assertEqual(result['broad']['captured_additions'], 731)
        self.assertEqual(result['history']['added_paths'], 17)

    def test_original_candidate_cannot_disappear(self):
        frame = self.broad['comparisons'][0]['changed_frames'][0]
        old = frame['before']['analysis']['analyses'][0]
        paths = [p for p in frame['after']['analysis']['analyses'] if p != old]
        self.reject_change(frame['after']['analysis'], 'analyses', paths, self.broad_check)

    def test_native_owner_cannot_disappear(self):
        owners = dict(self.owners['complete_native_entries'])
        owners.pop(next(iter(owners)))
        self.reject_change(self.owners, 'complete_native_entries', owners, self.broad_check)

    def test_added_candidate_must_have_individual_observation(self):
        self.reject_change(self.broad, 'individual_additions', self.broad['individual_additions'][:-1], self.broad_check)

    def test_spans_cannot_change(self):
        frame = self.broad['comparisons'][0]['changed_frames'][0]
        span = dict(frame['after']['span'])
        span['end'] += 1
        self.reject_change(frame['after'], 'span', span, self.broad_check)

    def test_prior_fingerprint_cannot_change(self):
        comparison = self.broad['comparisons'][0]
        self.reject_change(comparison, 'previous_capture_after_sha256', '0' * 64, self.broad_check)

    def test_compatibility_cannot_claim_contextual_correctness(self):
        row = next(r for r in self.broad['individual_additions'] if r['dictionary_assessment']['status'] == 'compatible')
        self.reject_change(row, 'contextual_verdict', 'correct', self.broad_check)

    def test_original_sentence_cannot_change(self):
        corpus = self.corpora['corpora'][0]
        self.reject_change(corpus, 'original_source_text', corpus['original_source_text'] + '\n', self.corpus_check)

    def test_adapter_gold_recovery_cannot_change_even_with_rehashed_output(self):
        stream = self.adapter['runs'][0]['streams'][0]
        replacement = copy.copy(stream)
        rows = [json.loads(line) for line in stream['jsonl'].splitlines()]
        rows[1]['recovered'] += 1
        replacement['jsonl'] = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows)
        replacement['sha256'] = a.sha(replacement['jsonl'].encode())
        run = self.adapter['runs'][0]
        # Alter both sides so byte equality alone cannot reject the forged data.
        other = dict(replacement, mode='after')
        self.reject_change(run, 'streams', [replacement, other], self.corpus_check)

    def test_candidate_count_cannot_change(self):
        row = self.corpora['corpora'][0]['comparisons'][0]['after']
        self.reject_change(row, 'candidates', row['candidates'] + 1, self.corpus_check)

    def test_corpus_partition_cannot_disappear(self):
        self.reject_change(self.corpora, 'corpora', self.corpora['corpora'][:-1], self.corpus_check)

    def test_historical_addition_cannot_be_reassigned(self):
        history = copy.deepcopy(self.history)
        row = next(iter(history['changes'].values()))
        row['origins'][0]['pointer'] = '/missing'
        with self.assertRaises(AssertionError):
            a.verify_history(history)


if __name__ == '__main__':
    unittest.main()
