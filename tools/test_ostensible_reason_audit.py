import copy
import json
import unittest
from pathlib import Path

import ostensible_reason_audit as audit


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = {
            'capture':audit.read(audit.ROOT/'docs/ostensible-reason-source-discovery.json.gz'),
            'preparation':audit.read(audit.ROOT/'docs/ostensible-reason-source-owner-preparation.json.gz'),
            'replay':audit.read(audit.ROOT/'docs/ostensible-reason-prototype-source-replay.json.gz'),
            'originals':audit.read(audit.ROOT/'tests/fixtures/ostensible-reason-original-cases.json'),
            'suite':audit.read(audit.ROOT/'tests/fixtures/ostensible-reason-validity.json'),
            'catalog':audit.read(audit.ROOT/'web/src/grammar-labels.json'),
        }

    def reject(self, key, mutate):
        inputs = dict(self.inputs)
        inputs[key] = copy.deepcopy(inputs[key])
        mutate(inputs[key])
        with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration)):
            audit.inspect(**inputs)

    def test_all_original_structures_and_unjudged_additions_are_individually_bound(self):
        result = audit.inspect(**self.inputs)
        self.assertEqual(result['source_required_additions'],72)
        self.assertEqual(result['unjudged_additions'],86)
        self.assertEqual(sum(bool(r['judgment_refs']) for r in result['individual_judgments']),72)

    def test_dialogue_reply_cannot_disappear(self):
        self.reject('capture',lambda r:r['all_original_groups'][3]['original'].pop())

    def test_original_source_span_cannot_move(self):
        self.reject('capture',lambda r:r['targets'][0]['char_span'].__setitem__('start',0))

    def test_native_marker_note_cannot_disappear(self):
        self.reject('preparation',lambda r:r['complete_native_entries']['krdict:80318']['senses'][0].__setitem__('notes',[]))

    def test_original_lmf_fields_cannot_disappear(self):
        self.reject('preparation',lambda r:r['original_lmf']['krdict:80316']['Sense'].__setitem__('SenseExample',[]))

    def test_present_label_cannot_borrow_plain_source(self):
        self.reject('catalog',lambda r:r['-는답시고']['sources'][0].__setitem__('id',80318))

    def test_a_source_requirement_cannot_become_a_global_lemma_ban(self):
        self.reject('suite',lambda r:r['cases'][0]['judgments'][0].__setitem__('verdict','forbidden'))

    def test_duplicate_mode_cannot_replace_nfd_compatible(self):
        self.reject('replay',lambda r:r['runs'].__setitem__(-1,r['runs'][0]))

    def test_frame_cannot_disappear_even_with_updated_hash(self):
        def mutate(report):
            run = report['runs'][0]
            run['jsonl'] = '\n'.join(run['jsonl'].splitlines()[:-1])+'\n'
            run['after_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject('replay',mutate)

    def test_existing_assessment_cannot_change_even_with_updated_stream_hash(self):
        def mutate(report):
            run = report['runs'][0]
            rows = list(map(json.loads,run['jsonl'].splitlines()))
            row = next(r for r in rows if r.get('analysis') and r['analysis']['analyses'])
            row['dictionary']['readings'][0]['status'] = 'invented'
            run['jsonl'] = '\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n'
            run['after_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject('replay',mutate)

    def test_observed_addition_cannot_disappear(self):
        self.reject('replay',lambda r:r['individual_additions'].pop())

    def test_unjudged_observation_cannot_self_certify_precision(self):
        self.reject('replay',lambda r:r['individual_additions'][0].__setitem__('structural_verdict','required'))

    def test_an_original_target_cannot_drop_a_filter_mode(self):
        self.reject('replay',lambda r:r['original_targets'].pop())


class LedgerGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = audit.historical_ledger()
        cls.current = audit.read(audit.ROOT/'tests/fixtures/validity.json')
        cls.suite = audit.read(audit.ROOT/'tests/fixtures/ostensible-reason-validity.json')

    def reject(self, mutate):
        current = copy.deepcopy(self.current)
        mutate(current)
        with self.assertRaises((AssertionError, KeyError)):
            audit.inspect_ledger(self.before, current, self.suite)

    def test_historical_cases_and_complete_append_are_exact(self):
        self.assertEqual(audit.inspect_ledger(self.before,self.current,self.suite)['new_individual_cases'],26)

    def test_old_judgment_cannot_change(self):
        self.reject(lambda r:r['cases'][0]['judgments'][0].__setitem__('verdict','invented'))

    def test_original_source_case_cannot_disappear(self):
        self.reject(lambda r:r['cases'].pop(len(self.before['cases'])))

    def test_old_source_url_cannot_change(self):
        self.reject(lambda r:r['sources'].__setitem__(next(iter(self.before['sources'])),'https://example.invalid'))

    def test_own_new_judgment_cannot_become_a_global_lemma_ban(self):
        self.reject(lambda r:r['cases'][len(self.before['cases'])]['judgments'][0].__setitem__('morphemes',[]))

    def test_old_case_id_cannot_be_reused(self):
        self.reject(lambda r:r['cases'].append(r['cases'][0]))


if __name__=='__main__':
    unittest.main()
