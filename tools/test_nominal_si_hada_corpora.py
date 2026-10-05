"""Reject lost candidate owners and rewritten annotated corpus evidence."""
import copy
import json
import unittest

import nominal_si_hada_corpora as corpus


class CorpusGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = corpus.read(corpus.REPORT)

    def test_complete_comparison(self):
        self.assertEqual(corpus.inspect(self.report), (66570, 32096, 6))

    def test_original_whole_candidate_cannot_disappear(self):
        report = copy.deepcopy(self.report)
        word = report["candidate_changes"][0]["surface"]
        parent = report["candidate_changes"][0]["parent"]
        report["after_words"][word]["analyses"].remove(parent)
        report["after_word_stream_sha256"] = corpus.digest(json.dumps(report["after_words"], ensure_ascii=False, sort_keys=True))
        with self.assertRaises(AssertionError):
            corpus.inspect(report)

    def test_annotated_gold_cannot_be_rewritten(self):
        report = copy.deepcopy(self.report)
        current = report["corpora"][0]
        rows = [json.loads(line) for line in current["after_jsonl"].splitlines()]
        rows[1]["surface"] = "rewritten"
        current["after_jsonl"] = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
        current["after_report_sha256"] = corpus.digest(current["after_jsonl"])
        with self.assertRaises(AssertionError):
            corpus.inspect(report)

    def test_candidate_case_cannot_borrow_another_parent(self):
        report = copy.deepcopy(self.report)
        report["candidate_changes"][0]["parent"]["lemmas"][0]["text"] = "하다"
        with self.assertRaises(AssertionError):
            corpus.inspect(report)
