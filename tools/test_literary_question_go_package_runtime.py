"""Reject corrupted actual CLI source, boundary, Native-mode and broad captures."""
import copy
import unittest
from functools import lru_cache
from unittest.mock import patch
import literary_question_go_runtime as audit

cached_read = lru_cache(maxsize=None)(audit.read)

class CliGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.read(audit.ROOT/'docs/literary-question-go-packaged-cli-replay.json')

    def setUp(self):
        patcher = patch.object(audit, 'read', cached_read)
        patcher.start()
        self.addCleanup(patcher.stop)

    def reject(self, mutate):
        report = copy.deepcopy(self.report)
        mutate(report)
        with self.assertRaises((AssertionError, KeyError, ValueError, StopIteration)):
            audit.verify_cli(report)

    def test_all_main_streams_pass(self):
        self.assertEqual(audit.verify_cli(self.report)['broad_frames'], 1128312)

    def test_actual_binary_is_bound(self):
        self.reject(lambda r: r.__setitem__('cli_sha256', '0'*64))

    def test_original_source_stream_is_bound(self):
        self.reject(lambda r: r['runs'].__setitem__(1, r['runs'][0]))

    def test_boundary_allomorph_stream_is_bound(self):
        self.reject(lambda r: r['boundary_runs'][0].__setitem__('sha256', '0'*64))

    def test_forbidden_judgment_cannot_be_required(self):
        def mutate(r):
            next(j for j in r['judgments'] if j['verdict']=='forbidden').update(
                verdict='required', present=True)
        self.reject(mutate)

    def test_conditional_native_output_is_bound(self):
        self.reject(lambda r: r['conditional_runs'][0].__setitem__('jsonl', ''))

    def test_broad_stream_cannot_disappear(self):
        self.reject(lambda r: r['broad'].pop())

    def test_corpus_word_digest_is_bound(self):
        self.reject(lambda r: r['corpora'].__setitem__('word_analyses_sha256', '0'*64))

    def test_context_cannot_be_certified(self):
        self.reject(lambda r: r.__setitem__('contextual_verdict', 'correct'))

    def test_changed_producer_cannot_self_certify(self):
        def mutate(r):
            r['producer']['text'] += '\n# altered\n'
            r['producer']['sha256'] = audit.sha(r['producer']['text'].encode())
        self.reject(mutate)

if __name__ == '__main__':
    unittest.main()
