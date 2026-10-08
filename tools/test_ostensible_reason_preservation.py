"""Mutation controls for exact observed-cohort conservation; no new gold invented."""
import copy
import importlib.util
import unittest
from pathlib import Path

import ostensible_reason_preservation as audit

class PreservationControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports=[audit.read(audit.ROOT/'docs'/('ostensible-reason-prototype-'+n+'.json.gz')) for n in ['broad','corpora','legacy-history']]
        cls.prior={str(audit.ROOT/p):audit.read(audit.ROOT/p) for p in ['docs/declarative-contrast-prototype-broad.json.gz','docs/declarative-contrast-prototype-corpora.json.gz','docs/declarative-contrast-prototype-legacy-history.json']}
        original=audit.read
        audit.read=lambda p:cls.prior.get(str(p)) if str(p) in cls.prior else original(p)

    def rejects(self,index,change):
        reports=list(self.reports);reports[index]=dict(reports[index]);change(reports[index])
        with self.assertRaises(AssertionError):audit.inspect(*reports)

    def test_unchanged_capture_passes(self):
        self.assertEqual(audit.inspect(*self.reports)['broad_frames'],1128312)

    def test_dropped_mode(self):
        self.rejects(0,lambda r:r.update(comparisons=r['comparisons'][:-1]))

    def test_dropped_frame(self):
        def mutate(r):
            r['comparisons']=copy.deepcopy(r['comparisons']);r['comparisons'][0]['records']-=1
        self.rejects(0,mutate)

    def test_altered_stream_even_with_equal_before_after_hashes(self):
        def mutate(r):
            r['comparisons']=copy.deepcopy(r['comparisons'])
            for key in ['before_jsonl_sha256','after_jsonl_sha256','previous_capture_after_sha256']:r['comparisons'][0][key]='0'*64
        self.rejects(0,mutate)

    def test_invented_broad_addition(self):
        self.rejects(0,lambda r:r.update(individual_additions=[{'structural_verdict':'required'}]))

    def test_missing_corpus_word_with_recomputed_hash(self):
        def mutate(r):
            r['after_words']=dict(r['after_words']);r['after_words'].pop(next(iter(r['after_words'])));r['after_words_sha256']=audit.digest(r['after_words'])
        self.rejects(1,mutate)

    def test_changed_gold_while_self_consistent(self):
        def mutate(r):
            r['corpora']=list(r['corpora']);item=dict(r['corpora'][0]);r['corpora'][0]=item
            item['original_converted_rows']=list(item['original_converted_rows']);row=dict(item['original_converted_rows'][0]);item['original_converted_rows'][0]=row
            row['expected']=['invented'];item['original_converted_rows_sha256']=audit.digest(item['original_converted_rows'])
        self.rejects(1,mutate)

    def test_missing_original_historical_archive(self):
        def mutate(r):
            r['source_files_sha256']=dict(r['source_files_sha256']);r['source_files_sha256'].pop(next(iter(r['source_files_sha256'])))
        self.rejects(2,mutate)

    def test_missing_historical_word_and_origin_even_with_recomputed_hashes(self):
        def mutate(r):
            surface=next(iter(r['origins']));r['origins']=dict(r['origins']);r['origins'].pop(surface)
            for key in ['before_words','after_words']:
                r[key]=dict(r[key]);r[key].pop(surface);r[key+'_sha256']=audit.digest(r[key])
            r['surfaces']-=1
        self.rejects(2,mutate)

    def test_altered_producer(self):
        def mutate(r):r['producer']=dict(r['producer']);r['producer']['text']+='\n# altered'
        self.rejects(0,mutate)

    def test_unproven_frozen_inputs(self):
        self.rejects(0,lambda r:r.update(inputs_unchanged=False))

if __name__=='__main__':unittest.main()
