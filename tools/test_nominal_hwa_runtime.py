"""Reject incomplete runtime, inventory-stream and corpus evidence."""
import copy
import unittest

import nominal_hwa_broad as broad
import nominal_hwa_corpora as corpora
import nominal_hwa_runtime as runtime
from well_doeda_audit import read


class RuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=read(runtime.REPORT)

    def test_complete_runtime(self):
        self.assertEqual(runtime.inspect(self.report),(1918,1204,164,10,6))

    def test_missing_api_chunk(self):
        report=copy.deepcopy(self.report);report['api']['batches'].pop()
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_encoding_label_cannot_replace_actual_nfd_input(self):
        report=copy.deepcopy(self.report)
        report['api']['batches'][16]['request']['text']=report['api']['batches'][0]['request']['text']
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_suffix_source_cannot_be_replaced_by_honorific(self):
        report=copy.deepcopy(self.report)
        report['browser']['responses'][0]['response']['grammar']['-화'][0]['pos']='어미'
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_diagram_cannot_drop_nested_suffix(self):
        report=copy.deepcopy(self.report);report['browser']['diagrams'][0]['parts'].pop(1)
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_nominal_hint_cannot_choose_the_thorn_homonym(self):
        report=copy.deepcopy(self.report)
        diagram=next(d for d in report['browser']['diagrams'] if d['word']=='가시화')
        diagram['entry']='krdict:14668'
        with self.assertRaises(AssertionError):runtime.inspect(report)



class StreamGuards(unittest.TestCase):
    def test_complete_broad(self):
        self.assertEqual(broad.inspect(read(broad.REPORT)),(1128312,0))

    def test_missing_broad_stream(self):
        report=read(broad.REPORT);report['comparisons'].pop()
        with self.assertRaises(AssertionError):broad.inspect(report)

    def test_complete_corpora(self):
        self.assertEqual(corpora.inspect(read(corpora.REPORT)),(66570,32096,18))

    def test_missing_source_parent_addition(self):
        report=read(corpora.REPORT);report['candidate_changes'].pop()
        with self.assertRaises(AssertionError):corpora.inspect(report)

    def test_missing_original_word(self):
        report=read(corpora.REPORT);report['after_words'].pop(next(iter(report['after_words'])))
        with self.assertRaises(AssertionError):corpora.inspect(report)


if __name__=='__main__':unittest.main()
