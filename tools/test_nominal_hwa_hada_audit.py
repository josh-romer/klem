"""Reject incomplete sources and forged direct/nested -하다 evidence."""
import copy
import unittest

import nominal_hwa_hada_audit as audit


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=audit.read(audit.SOURCE)

    def test_complete_sources(self):
        self.assertEqual(audit.inspect_source(self.source),(1154,562,165,30))

    def test_missing_hada_sense(self):
        s=copy.deepcopy(self.source);s['complete_native_entries']['krdict:88475']['senses'].pop()
        with self.assertRaises(AssertionError):audit.inspect_source(s)

    def test_direct_origin_cannot_borrow_deeper_base(self):
        s=copy.deepcopy(self.source);s['complete_native_entries']['krdict:71858']['origins']=['義人化']
        with self.assertRaises(AssertionError):audit.licenses(s)

    def test_unresolved_nested_class_cannot_be_promoted(self):
        s=copy.deepcopy(self.source);next(f for f in s['families'] if f['base']=='간소')['verbal_supported']=True
        with self.assertRaises(AssertionError):audit.licenses(s)

    def test_missing_original_row(self):
        s=copy.deepcopy(self.source);next(c for c in s['corpora'] if c['rows'])['rows'].pop()
        with self.assertRaises(AssertionError):audit.inspect_source(s)


class ComparisonGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=audit.read(audit.SOURCE);cls.report=audit.read(audit.REPORT)

    def test_complete_comparison(self):
        self.assertEqual(audit.inspect_comparison(self.source,self.report),3408)

    def test_missing_cache_encoding(self):
        r=copy.deepcopy(self.report);del r['runs']['compatible']['NFD-uncached']
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,r)

    def test_changed_original_reading(self):
        r=copy.deepcopy(self.report);r['changes'][0]['parent']['unchanged']=True
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,r)

    def test_forged_origin_relation(self):
        r=copy.deepcopy(self.report)
        entry=next(e for c in r['changes'] for e in c['reading']['lemmas'][0]['entries'] if e.get('derivational_identity'))
        entry['derivational_identity']['relation']='unknown'
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,r)

    def test_nominal_source_cannot_replace_verbal_owner(self):
        r=copy.deepcopy(self.report)
        entry=next(e for c in r['changes'] for e in c['reading']['lemmas'][0]['entries'] if e.get('derivational_identity'))
        entry['derivational_identity']['whole_entries']=['krdict:14680']
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,r)

    def test_wrong_owned_suffix_index(self):
        r=copy.deepcopy(self.report)
        c=next(c for c in r['changes'] if c['analysis']['morphemes'][0]['form']=='화')
        entry=next(e for e in c['reading']['lemmas'][0]['entries'] if e.get('derivational_identity'))
        entry['derivational_identity']['morpheme_index']=0
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,r)


if __name__=='__main__':unittest.main()
