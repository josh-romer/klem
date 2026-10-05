"""Reject missing original sources, lost readings and unsupported noun-hada evidence."""
import copy
import unittest

import hada_nominal_audit as audit


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = audit.read(audit.SOURCE)

    def test_complete_sources(self):
        self.assertEqual(len(audit.inspect_source(self.source)), 11)

    def test_missing_unimplemented_sense(self):
        source = copy.deepcopy(self.source)
        source['complete_native_entries']['krdict:88475']['senses'].pop()
        with self.assertRaises(AssertionError):
            audit.inspect_source(source)

    def test_wrong_predicate_class(self):
        source = copy.deepcopy(self.source)
        source['owners'][6]['supported_predicate_classes'] = ['동사']
        with self.assertRaises(AssertionError):
            audit.inspect_source(source)

    def test_missing_original_context(self):
        source = copy.deepcopy(self.source)
        next(c for c in source['corpora'] if c['rows'])['rows'].pop()
        with self.assertRaises(AssertionError):
            audit.inspect_source(source)


class ComparisonGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = audit.read(audit.SOURCE)
        cls.report = audit.read(audit.REPORT)

    def test_complete_comparison(self):
        self.assertEqual(len(audit.inspect_comparison(self.source, self.report)), 1062)

    def test_missing_encoding_cache_stream(self):
        report = copy.deepcopy(self.report)
        del report['runs']['compatible']['NFD-uncached']
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_forged_parent(self):
        report = copy.deepcopy(self.report)
        report['changes'][0]['parent']['unchanged'] = True
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_missing_origin_cannot_be_difference(self):
        report = copy.deepcopy(self.report)
        change = next(c for c in report['changes'] if c['surface'] == '사랑하다')
        entry = next(e for e in change['reading']['lemmas'][0]['entries'] if e['id'] == 'krdict:61680')
        entry['derivational_identity']['relation'] = 'recorded_difference'
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_original_reading_cannot_change(self):
        report = copy.deepcopy(self.report)
        change = report['changes'][0]
        change['reading']['lemmas'][0]['entries'][0]['id'] = 'krdict:31765'
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_parent_cannot_borrow_recovery(self):
        owners = audit.inspect_source(self.source)
        _, before = audit.word_records(self.source['before']['raw']['jsonl'])
        change = self.report['changes'][0]
        analysis = copy.deepcopy(change['analysis'])
        analysis['spelling_paths'] = [[{'morpheme_index': 0, 'kind': 'hieut_irregular'}]]
        with self.assertRaises(AssertionError):
            audit.parent_for(owners, change['surface'], analysis, before)


if __name__ == '__main__':
    unittest.main()
