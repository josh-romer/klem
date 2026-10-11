"""Reject altered old/new judgments even when an output digest is repaired."""
import copy
import json
import unittest
import conjectural_additive_ledger_audit as audit

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.values = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.values)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason): audit.inspect(values)

    def change(self, values, mutate):
        ledger = json.loads(values['after_raw'])
        mutate(ledger)
        values['after_raw'] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()
        values['append']['after_ledger_sha256'] = audit.sha(values['after_raw'])

    def test_exact_complete_append(self):
        self.assertEqual(audit.inspect(self.values)['cases'], 35643)

    def test_old_lemma_changed_with_hash_repaired(self):
        self.reject(lambda v: self.change(v, lambda d: d['cases'][0]['judgments'][0]['lemmas'].__setitem__(0, 'invented')), 'every old case/role/morpheme/rule/verdict/reason retained')

    def test_old_source_removed_with_hash_repaired(self):
        self.reject(lambda v: self.change(v, lambda d: d['sources'].pop(next(iter(json.loads(v['before_raw'])['sources'])))), 'every old source citation retained')

    def test_new_required_structure_erased(self):
        self.reject(lambda v: self.change(v, lambda d: d['cases'].pop()), 'exact complete ledger sizes')

    def test_new_nominal_role_corrupted_with_hash_repaired(self):
        self.reject(lambda v: self.change(v, lambda d: d['cases'][35622]['judgments'][0]['lemma_kinds'].__setitem__(0, 'predicate')), 'only41exactindependentlyauthoredcases appended')

    def test_forbidden_coda_case_promoted_with_hash_repaired(self):
        self.reject(lambda v: self.change(v, lambda d: d['cases'][35624]['judgments'][0].update(verdict='required')), 'only41exactindependentlyauthoredcases appended')

    def test_authored_source_changed_to_fit_output(self):
        def mutate(v):
            d = json.loads(v['source_raw']); d['cases'][0]['judgments'][0]['lemmas'][0] = 'invented'
            v['source_raw'] = (json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'original35authoredjudgments unchanged')

    def test_original_serialization_reformatted(self):
        def mutate(v):
            v['after_raw'] = (json.dumps(json.loads(v['after_raw']), ensure_ascii=False) + '\n').encode()
        self.reject(mutate, 'every original serialized case byte retained')

    def test_append_ids_fabricated(self):
        self.reject(lambda v: v['append']['independent_appended_case_ids'].pop(), 'exact independent append IDs')

    def current(self, values, mutate):
        ledger = json.loads(values['current_raw'])
        mutate(ledger)
        values['current_raw'] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()
        values['novel_append']['after_ledger_sha256'] = audit.sha(values['current_raw'])

    def test_prior_case_changed_in_current_with_hash_repaired(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][0]['judgments'][0]['lemmas'].__setitem__(0, 'invented')), 'every35628previouscase retained')

    def test_novel_adverb_role_changed_with_hash_repaired(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][35630]['judgments'][0]['lemma_kinds'].__setitem__(0, 'nominal')), 'only15independentnovelcases appended')

    def test_novel_alternative_erased_with_hash_repaired(self):
        self.reject(lambda v: self.current(v, lambda d: d['cases'][35629]['judgments'].pop()), 'only15independentnovelcases appended')

    def test_novel_target_rewritten_to_match_output(self):
        def mutate(v):
            d = json.loads(v['novel_raw'])
            d['cases'][11]['judgments'][0]['lemmas'] = ['나', '이다']
            v['novel_raw'] = (json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(mutate, 'independent16novelrequirements unchanged')

    def test_novel_append_ids_fabricated(self):
        self.reject(lambda v: v['novel_append']['independent_appended_case_ids'].pop(), 'exact independent novel append identities')

if __name__ == '__main__': unittest.main()
