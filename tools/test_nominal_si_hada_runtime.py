"""Reject incomplete API, native-entry, diagram and export evidence."""
import copy
import unittest

import nominal_si_hada_runtime as runtime


class RuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=runtime.read(runtime.REPORT)

    def reject(self,report):
        with self.assertRaises(AssertionError):runtime.inspect(report)

    def test_complete_runtime(self):self.assertEqual(runtime.inspect(self.report),(410,700,49,10,6))

    def test_missing_nfd_batch(self):
        r=copy.deepcopy(self.report);r['api']['batches'].pop();self.reject(r)

    def test_forged_export(self):
        r=copy.deepcopy(self.report);r['browser']['checks'][0]['exported_records'].pop();self.reject(r)

    def test_missing_native_hada_sense(self):
        r=copy.deepcopy(self.report);r['api']['complete_native_entries']['krdict:88475']['senses'].pop();self.reject(r)

    def test_wrong_nominal_identity_index(self):
        r=copy.deepcopy(self.report);d=next(d for d in r['browser']['diagrams'] if not d['nested'] and not d['no_entry']);e=next(e for e in d['owner']['entries'] if e['id']==d['entry']);e['derivational_identity']['morpheme_index']=1;self.reject(r)

    def test_wrong_nested_origin_relation(self):
        r=copy.deepcopy(self.report);d=next(d for d in r['browser']['diagrams'] if d['nested']);e=next(e for e in d['owner']['entries'] if e['id']==d['entry']);e['derivational_identity']['relation']='unknown';self.reject(r)

    def test_wrong_homonym_hint(self):
        r=copy.deepcopy(self.report);d=next(d for d in r['browser']['diagrams'] if d['word']=='등한시했어요');d['entry']='krdict:14668';self.reject(r)

    def test_unexpanded_hada_past(self):
        r=copy.deepcopy(self.report);d=next(d for d in r['browser']['diagrams'] if d['word']=='등한시했어요');d['parts'][2]='었';self.reject(r)

    def test_missing_entry_cannot_borrow_whole_gloss(self):
        r=copy.deepcopy(self.report);d=next(d for d in r['browser']['diagrams'] if d['no_entry']);d['label']='treat as a problem';self.reject(r)

    def test_missing_entry_cannot_claim_dictionary_senses(self):
        r=copy.deepcopy(self.report);d=next(d for d in r['browser']['diagrams'] if d['no_entry']);d['title']+='; click for all senses';self.reject(r)

    def test_reordered_direct_components(self):
        r=copy.deepcopy(self.report);d=next(d for d in r['browser']['diagrams'] if not d['nested'] and not d['no_entry']);d['parts'][:2]=['하',d['base']];self.reject(r)


if __name__=='__main__':unittest.main()
