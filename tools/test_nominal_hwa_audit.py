"""Keep omitted evidence and invented suffix candidates from passing the audit."""
import copy
import hashlib
import json
import unittest

import nominal_hwa_audit as audit


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=audit.read(audit.SOURCE)

    def test_complete_source(self):
        self.assertEqual(audit.inspect_source(self.source),(583,953,164,185))

    def test_wrong_suffix_role(self):
        source=copy.deepcopy(self.source)
        source['complete_native_entries']['krdict:88499']['pos']='어미'
        with self.assertRaises(AssertionError):audit.inspect_source(source)

    def test_opaque_base_cannot_be_declared_reviewed(self):
        source=copy.deepcopy(self.source)
        next(f for f in source['families'] if f['head']=='간소화')['nominal_supported']=True
        with self.assertRaises(AssertionError):audit.inspect_source(source)

    def test_unlisted_passive_cannot_be_inherited(self):
        source=copy.deepcopy(self.source)
        next(f for f in source['families'] if f['head']=='개념화')['passive_supported']=True
        with self.assertRaises(AssertionError):audit.inspect_source(source)

    def test_before_stream_may_not_be_rewritten(self):
        source=copy.deepcopy(self.source)
        source['before']['raw']['jsonl']+='{}\n'
        with self.assertRaises(AssertionError):audit.inspect_source(source)


class ComparisonGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=audit.read(audit.SOURCE)
        cls.report=audit.read(audit.REPORT)

    def test_complete_comparison(self):
        self.assertEqual(audit.inspect_comparison(self.source,self.report),1806)

    def test_missing_encoding_cache_pair(self):
        report=copy.deepcopy(self.report)
        del report['runs']['compatible']['NFD-uncached']
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,report)

    def rewrite_raw_candidate(self,mutate,word='상품화되는'):
        report=copy.deepcopy(self.report)
        for run in report['runs']['raw'].values():
            rows=[json.loads(line) for line in run['jsonl'].splitlines()]
            record=next(r for r in rows if (r.get('analysis') or {}).get('normalized')==word)
            index=next(i for i,a in enumerate(record['analysis']['analyses']) if audit.RULE in a['rules'])
            mutate(record,index)
            run['jsonl']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
            run['sha256']=hashlib.sha256(run['jsonl'].encode()).hexdigest()
        return report

    def test_invented_tail_has_no_preserved_parent(self):
        def mutate(record,index):record['analysis']['analyses'][index]['morphemes'][-1]['form']='invented'
        report=self.rewrite_raw_candidate(mutate)
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,report)

    def test_invented_rule_has_no_preserved_parent(self):
        def mutate(record,index):record['analysis']['analyses'][index]['rules'].append('invented.rule')
        report=self.rewrite_raw_candidate(mutate)
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,report)

    def test_borrowed_whole_head_identity(self):
        def mutate(record,index):
            owner=record['dictionary']['readings'][index]['lemmas'][0]
            entry=next(e for e in owner['entries'] if e.get('derivational_identity'))
            entry['derivational_identity']['whole_entries']=['krdict:14682']
        report=self.rewrite_raw_candidate(mutate)
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,report)

    def test_nominal_cannot_borrow_passive_identity(self):
        def mutate(record,index):
            entry=next(e for e in record['dictionary']['readings'][index]['lemmas'][0]['entries'] if e['id']=='krdict:14669')
            entry['derivational_identity']['whole_entries']=['krdict:14682']
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,self.rewrite_raw_candidate(mutate,'가시화'))

    def test_missing_nominal_origin_evidence(self):
        def mutate(record,index):
            entry=next(e for e in record['dictionary']['readings'][index]['lemmas'][0]['entries'] if e['id']=='krdict:14669')
            del entry['derivational_identity']
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,self.rewrite_raw_candidate(mutate,'가시화'))

    def test_different_origin_cannot_become_a_recorded_match(self):
        def mutate(record,index):
            entry=next(e for e in record['dictionary']['readings'][index]['lemmas'][0]['entries'] if e.get('derivational_identity',{}).get('relation')=='recorded_difference')
            entry['derivational_identity']['relation']='recorded_match'
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,self.rewrite_raw_candidate(mutate))

    def test_missing_individual_change(self):
        report=copy.deepcopy(self.report);report['changes'].pop()
        with self.assertRaises(AssertionError):audit.inspect_comparison(self.source,report)


if __name__=='__main__':unittest.main()
