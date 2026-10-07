import copy
import json
import unittest
from pathlib import Path
import declarative_contrast_audit as a


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f = a.ROOT / 'tests/fixtures'
        cls.inputs = [a.read(a.ROOT / 'docs/declarative-contrast-source-discovery.json.gz'),
                      a.read(a.ROOT / 'docs/declarative-contrast-broad-owner-preparation.json.gz'),
                      a.read(a.ROOT / 'docs/declarative-contrast-target-observations.json'),
                      a.read(f / 'declarative-contrast-validity.json'),
                      a.read(f / 'declarative-contrast-original-cases.json'),
                      a.read(a.ROOT / 'web/src/grammar-labels.json'),
                      a.read(a.ROOT / 'docs/declarative-contrast-prototype-source-replay.json.gz'),
                      a.read(a.ROOT / 'docs/declarative-contrast-prototype-source-target-audit.json.gz')]

    def reject(self, mutation):
        inputs = copy.deepcopy(self.inputs)
        mutation(inputs)
        with self.assertRaises((AssertionError, KeyError, ValueError, StopIteration)):
            a.verify_sources(*inputs)

    def alter_frame(self, inputs, encoding, mode, surface, change):
        run = next(r for r in inputs[6]['runs'] if (r['encoding'],r['mode']) == (encoding,mode))
        frames = list(map(json.loads, run['jsonl'].splitlines()))
        frame = next(f for f in frames if f.get('analysis') and f['analysis']['normalized'] == surface)
        change(frame)
        run['jsonl'] = '\n'.join(json.dumps(f, ensure_ascii=False) for f in frames)+'\n'
        run['after_sha256'] = a.sha(run['jsonl'].encode())

    def test_complete_actual_sources_and_replay(self):
        self.assertEqual(a.verify_sources(*self.inputs)['exact_occurrence_observations'],144)

    def test_dialogue_reply_cannot_disappear(self):
        self.reject(lambda d: d[0]['all_original_groups'][-1]['original'].pop())

    def test_lexical_source_note_cannot_disappear(self):
        self.reject(lambda d: d[1]['complete_native_entries']['krdict:80321']['senses'][0]['notes'].clear())

    def test_homonym_cannot_disappear(self):
        self.reject(lambda d: d[1]['complete_native_entries'].pop('krdict:54855'))

    def test_whole_connective_cannot_borrow_particle_source(self):
        self.reject(lambda d: d[5]['-다만']['sources'][0].__setitem__('id',86555))

    def test_duplicate_stream_cannot_replace_nfd_compatible(self):
        self.reject(lambda d: d[6]['runs'].__setitem__(-1,d[6]['runs'][0]))

    def test_exact_occurrence_span_cannot_move(self):
        self.reject(lambda d: d[4][0]['source_occurrence']['character_span'].__setitem__(0,0))

    def test_added_path_cannot_disappear_from_individual_tracking(self):
        self.reject(lambda d: d[6]['additions'].pop())

    def test_duplicate_observation_cannot_replace_last_target(self):
        self.reject(lambda d: d[7]['required_source_occurrence_observations'].__setitem__(-1,d[7]['required_source_occurrence_observations'][0]))

    def test_previous_particle_path_cannot_disappear_even_with_updated_stream_hash(self):
        def change(d):
            def drop(f):
                n = next(i for i,p in enumerate(f['analysis']['analyses']) if 'particle.concessive' in p['rules'])
                f['analysis']['analyses'].pop(n)
                f['dictionary']['readings'].pop(n)
            self.alter_frame(d,'NFC','raw','없다마는',drop)
        self.reject(change)

    def test_isolated_hada_cannot_become_contextually_licensed(self):
        def change(d):
            def upgrade(f):
                for i,p in enumerate(f['analysis']['analyses']):
                    if 'ending.declarative_contrast' in p['rules']:
                        f['dictionary']['readings'][i]['status'] = 'compatible'
            self.alter_frame(d,'NFC','compatible','하다만',upgrade)
        self.reject(change)

    def test_forbidden_present_stem_cannot_turn_into_required(self):
        def change(d):
            j = next(j for c in d[3]['cases'] for j in c['judgments'] if j['verdict']=='forbidden')
            j['verdict']='required'
        self.reject(change)


if __name__ == '__main__':
    unittest.main()
