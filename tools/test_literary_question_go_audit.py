"""Mutation controls for the actual complete source replay and Native closure."""
import copy
import importlib.util
import unittest
from pathlib import Path

import literary_question_go_audit as audit

class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=[audit.read(audit.ROOT/'docs/literary-question-go-source-discovery.json.gz'),
                    audit.read(audit.ROOT/'docs/literary-question-go-source-owner-preparation.json.gz'),
                    audit.read(audit.ROOT/'docs/literary-question-go-prototype-source-replay.json.gz'),
                    audit.read(audit.ROOT/'tests/fixtures/literary-question-go-original-cases.json'),
                    audit.read(audit.ROOT/'web/src/grammar-labels.json')]
    def reject(self,index,mutate):
        rows=list(self.inputs);rows[index]=copy.deepcopy(rows[index]);mutate(rows[index])
        with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration)):
            audit.inspect(*rows)
    def test_all_complete_original_data_passes(self):
        result=audit.inspect(*self.inputs)
        self.assertEqual(result['original_required_observations'],234)
        self.assertEqual(result['unjudged_additions'],552)
    def test_original_group_cannot_disappear(self):
        self.reject(0,lambda r:r['all_original_groups'].pop())
    def test_original_native_examples_cannot_be_rewritten(self):
        self.reject(1,lambda r:r['complete_native_entries']['krdict:73889']['senses'][0]['examples'].pop())
    def test_matched_native_owner_cannot_disappear(self):
        self.reject(1,lambda r:r['matched_native_owner_ids'].pop())
    def test_individual_case_cannot_disappear(self):
        self.reject(3,lambda r:r.pop())
    def test_new_observation_cannot_be_self_certified(self):
        self.reject(2,lambda r:r['individual_additions'][0].__setitem__('structural_verdict','required'))
    def test_new_observation_cannot_disappear(self):
        self.reject(2,lambda r:r['individual_additions'].pop())
    def test_stable_observation_id_cannot_be_replaced(self):
        self.reject(2,lambda r:r['individual_additions'][0].__setitem__('id','invented'))
    def test_contradictory_note_source_cannot_disappear(self):
        self.reject(1,lambda r:r['complete_native_entries']['krdict:73892'].__setitem__('notes',[]))
    def test_source_label_cannot_be_reassigned(self):
        self.reject(4,lambda r:r['-은고']['sources'][0].__setitem__('id',73892))
    def test_register_cannot_be_certified_by_structural_presence(self):
        self.reject(3,lambda r:r[0].__setitem__('contextual_verdict','correct'))

class LedgerGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ostensible_reason_sources import package_source_texts
        cls.before = audit.json.loads(package_source_texts(audit.read(
            audit.ROOT/'docs/ostensible-reason-package-nix.json'))['tests/fixtures/validity.json'])
        cls.current = audit.read(audit.ROOT/'tests/fixtures/validity.json')
        cls.proposal = audit.read(audit.ROOT/'docs/literary-question-go-append-only-ledger-proposal.json.gz')

    def reject(self, mutate):
        current = copy.deepcopy(self.current)
        mutate(current)
        with self.assertRaises((AssertionError, KeyError)):
            audit.verify_ledger(self.before, current, self.proposal)

    def test_exact_append_passes(self):
        self.assertEqual(audit.verify_ledger(self.before, self.current, self.proposal)[
            'new_individual_cases'], 62)

    def test_old_case_cannot_disappear(self):
        self.reject(lambda current: current['cases'].pop(0))

    def test_new_case_cannot_disappear(self):
        self.reject(lambda current: current['cases'].pop(34781))

    def test_required_cannot_be_changed_to_forbidden(self):
        self.reject(lambda current: current['cases'][34781]['judgments'][0].__setitem__(
            'verdict', 'forbidden'))

    def test_source_cannot_be_reassigned(self):
        self.reject(lambda current: current['sources'].__setitem__(
            'literary-question-go-73889', 'https://invalid.example'))

    def test_case_id_cannot_be_duplicated(self):
        self.reject(lambda current: current['cases'].append(current['cases'][0]))


if __name__ == '__main__':
    unittest.main()
