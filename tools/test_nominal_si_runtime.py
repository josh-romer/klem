"""Reject incomplete runtime, inventory-stream and corpus evidence."""
import copy
import unittest

import nominal_si_broad as broad
import nominal_si_corpora as corpora
import nominal_si_runtime as runtime
from well_doeda_audit import read


class RuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=read(runtime.REPORT)

    def test_complete_runtime(self):
        self.assertEqual(runtime.inspect(self.report),(504,282,44,8,6))

    def test_missing_api_chunk(self):
        report=copy.deepcopy(self.report);report['api']['batches'].pop()
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_encoding_label_cannot_replace_actual_nfd_input(self):
        report=copy.deepcopy(self.report)
        report['api']['batches'][4]['request']['text']=report['api']['batches'][0]['request']['text']
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_suffix_source_cannot_be_replaced_by_honorific(self):
        report=copy.deepcopy(self.report)
        report['browser']['responses'][0]['response']['grammar']['-시'][0]['pos']='어미'
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_diagram_cannot_drop_nested_suffix(self):
        report=copy.deepcopy(self.report);report['browser']['diagrams'][0]['parts'].pop(1)
        with self.assertRaises(AssertionError):runtime.inspect(report)


class StreamGuards(unittest.TestCase):
    def test_complete_broad(self):
        self.assertEqual(broad.inspect(read(broad.REPORT)),(1128312,0))

    def test_missing_broad_stream(self):
        report=read(broad.REPORT);report['comparisons'].pop()
        with self.assertRaises(AssertionError):broad.inspect(report)

    def test_complete_corpora(self):
        self.assertEqual(corpora.inspect(read(corpora.REPORT)),(66570,32096,0))

    def test_missing_original_word(self):
        report=read(corpora.REPORT);report['after_words'].pop(next(iter(report['after_words'])))
        with self.assertRaises(AssertionError):corpora.inspect(report)


if __name__=='__main__':unittest.main()
