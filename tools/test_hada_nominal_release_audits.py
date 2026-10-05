"""Mutation guards for full original streams and annotated corpus receipts."""
import copy
import unittest

import hada_nominal_broad as broad
import hada_nominal_corpora as corpora


class BroadGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = broad.read(broad.REPORT)

    def test_complete_streams(self):
        changes, metadata = broad.inspect(self.report)
        self.assertEqual((len(changes), len(metadata)), (3763, 435))

    def test_lost_original_path(self):
        report = copy.deepcopy(self.report)
        report['changed_record_pairs'][0]['after']['analysis']['analyses'] = []
        with self.assertRaises(AssertionError):
            broad.inspect(report)

    def test_changed_original_entry(self):
        report = copy.deepcopy(self.report)
        report['origin_field_changes'][0]['after']['origins'] = ['偽']
        with self.assertRaises(AssertionError):
            broad.inspect(report)

    def test_forged_parent(self):
        report = copy.deepcopy(self.report)
        report['candidate_changes'][0]['parent']['unchanged'] = True
        with self.assertRaises(AssertionError):
            broad.inspect(report)


class CorpusGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = corpora.read(corpora.REPORT)

    def test_complete_gold_and_paths(self):
        self.assertEqual(corpora.inspect(self.report), (66570, 32096, 56))

    def test_changed_gold(self):
        report = copy.deepcopy(self.report)
        report['corpora'][0]['changed_gold_outcomes'].append({'id': 'fake'})
        with self.assertRaises(AssertionError):
            corpora.inspect(report)

    def test_lost_source_context(self):
        report = copy.deepcopy(self.report)
        report['candidate_changes'][0]['occurrences'] = []
        with self.assertRaises(AssertionError):
            corpora.inspect(report)

    def test_forged_parent(self):
        report = copy.deepcopy(self.report)
        report['candidate_changes'][0]['parent']['unchanged'] = True
        with self.assertRaises(AssertionError):
            corpora.inspect(report)


if __name__ == '__main__':
    unittest.main()
