"""Reject unsupported source classes, invented identities and lost historical paths."""
import copy
import unittest

import hada_remaining_audit as audit


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = audit.read(audit.SOURCE)

    def test_complete_source(self):
        self.assertEqual(len(audit.inspect_source(self.source)), 17)

    def test_missing_dual_class(self):
        source = copy.deepcopy(self.source)
        owner = next(o for o in source['owners'] if len(o['supported_predicate_classes']) == 2)
        owner['supported_predicate_classes'].pop()
        with self.assertRaises(AssertionError):
            audit.inspect_source(source)

    def test_root_cannot_be_standalone_noun(self):
        source = copy.deepcopy(self.source)
        next(o for o in source['owners'] if o['base_role'] == 'root')['base_role'] = 'nominal'
        with self.assertRaises(AssertionError):
            audit.inspect_source(source)

    def test_auxiliary_cannot_borrow_lexical_homonym(self):
        source = copy.deepcopy(self.source)
        owner = next(o for o in source['owners'] if o['excluded_whole_homonyms'])
        owner['whole_entries'].append(owner['excluded_whole_homonyms'][0])
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
        cls.owners = audit.inspect_source(cls.source)
        _, cls.before = audit.word_records(cls.source['before']['raw']['jsonl'])

    def test_complete_comparison(self):
        changes, fields = audit.inspect_comparison(self.source, self.report)
        self.assertEqual((len(changes), len(fields)), (1084, 3))

    def test_missing_unicode_cache_stream(self):
        report = copy.deepcopy(self.report)
        del report['runs']['compatible']['NFD-uncached']
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_forged_retained_parent(self):
        report = copy.deepcopy(self.report)
        report['changes'][0]['parent']['unchanged'] = True
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_missing_origin_cannot_imply_difference(self):
        report = copy.deepcopy(self.report)
        entry = next(e for c in report['changes'] for l in c['reading']['lemmas']
                     for e in l['entries'] if e.get('derivational_identity', {}).get('relation') == 'unknown')
        entry['derivational_identity']['relation'] = 'recorded_difference'
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_origin_field_requires_native_evidence(self):
        report = copy.deepcopy(self.report)
        report['origin_field_changes'][0]['after_entry']['origins'] = ['invented']
        with self.assertRaises(AssertionError):
            audit.inspect_comparison(self.source, report)

    def test_owner_cannot_borrow_spelling_recovery(self):
        change = self.report['changes'][0]
        analysis = copy.deepcopy(change['analysis'])
        analysis['spelling_paths'] = [[{
            'morpheme_index': change['inserted_components'][0]['morpheme_index'],
            'class': 'hieut_irregular',
        }]]
        with self.assertRaises(AssertionError):
            audit.parent_for(self.owners, change['surface'], analysis,
                             self.before[change['surface']]['analysis']['analyses'])


if __name__ == '__main__':
    unittest.main()
