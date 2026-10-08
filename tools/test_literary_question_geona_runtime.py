"""Corrupt actual retained runtime or scoped ledger evidence, never synthetic success."""
import copy,os,unittest
from pathlib import Path
import literary_question_geona_runtime as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.report=audit.read(Path(os.environ.get('KLEM_GEONA_RUNTIME',str(audit.ROOT/'docs/literary-question-geona-main-cli-replay.json.gz'))));cls.current=audit.read(audit.ROOT/'tests/fixtures/validity.json');cls.proposal=audit.read(audit.ROOT/'docs/literary-question-geona-proposed-ledger.json.gz')
 def corrupt(self,change,reason):
  r=copy.deepcopy(self.report);change(r)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(r)
 def test_actual_full_runtime_passes(self):self.assertEqual(audit.inspect(self.report)['broad_frames'],1128312)
 def test_actual_append_only_ledger_passes(self):self.assertEqual(audit.verify_ledger(self.current,self.proposal)['preserved_cases'],34920)
 def test_nonterminal_capture(self):self.corrupt(lambda r:r.update(state='running'),'terminal')
 def test_source_file_missing(self):self.corrupt(lambda r:r['snapshot_files'].pop(next(iter(r['snapshot_files']))),'source scope')
 def test_source_bytes_wrong(self):self.corrupt(lambda r:r['snapshot_files']['src/engine.rs'].update(sha256='0'*64),'source scope')
 def test_producer_replaced(self):self.corrupt(lambda r:r['producer'].update(text='wrong'),'producer bytes')
 def test_source_filter_mode_missing(self):self.corrupt(lambda r:r['finite_runs'].pop(),'every exact finite')
 def test_finite_output_wrong(self):self.corrupt(lambda r:r['finite_runs'][0].update(jsonl_sha256='0'*64),'every exact finite')
 def test_mode_duplicated(self):self.corrupt(lambda r:r['finite_runs'].__setitem__(1,copy.deepcopy(r['finite_runs'][0])),'every exact finite')
 def test_full_stream_missing(self):self.corrupt(lambda r:r['broad'].pop(),'eight complete')
 def test_full_stream_changed(self):self.corrupt(lambda r:r['broad'][0].update(sha256='0'*64),'full broad output')
 def test_full_stream_input_changed(self):self.corrupt(lambda r:r['broad'][0].update(source_sha256='0'*64),'original broad input')
 def test_spacing_flag_removed(self):self.corrupt(lambda r:r['broad'][-1]['command'].remove('--suggest-spacing'),'broad flags')
 def test_corpus_word_removed(self):self.corrupt(lambda r:r['words'][0].update(surfaces=32095),'WordAnalysis outputs')
 def test_history_output_changed(self):self.corrupt(lambda r:r['words'][1].update(actual_word_analysis_sha256='0'*64),'WordAnalysis outputs')
 def test_prior_judgment_changed(self):
  c=copy.deepcopy(self.current);c['cases'][0]['judgments'][0]['verdict']='forbidden'
  with self.assertRaisesRegex(AssertionError,'append-only ledger'):audit.verify_ledger(c,self.proposal)
 def test_conditional_promoted(self):
  c=copy.deepcopy(self.current);c['cases'].append(copy.deepcopy(c['cases'][-1]));c['cases'][-1]['id']=self.proposal['excluded_conditional_native_cases'][0]['id']
  with self.assertRaisesRegex(AssertionError,'append-only ledger'):audit.verify_ledger(c,self.proposal)
 def test_exact_historical_ledger_still_passes(self):
  self.assertEqual(audit.verify_ledger(self.proposal['proposed_ledger'],self.proposal)['new_required'],50)
 def test_unreviewed_tail_cannot_pass(self):
  c=copy.deepcopy(self.current);extra=copy.deepcopy(c['cases'][-1]);extra['id']='unreviewed-extra';c['cases'].append(extra)
  with self.assertRaisesRegex(AssertionError,'append-only ledger'):audit.verify_ledger(c,self.proposal)
 def test_later_judgment_change_cannot_pass(self):
  c=copy.deepcopy(self.current);c['cases'][-1]['judgments'][0]['verdict']='required' if c['cases'][-1]['judgments'][0]['verdict']=='forbidden' else 'forbidden'
  with self.assertRaisesRegex(AssertionError,'append-only ledger'):audit.verify_ledger(c,self.proposal)
 def test_later_source_change_cannot_pass(self):
  c=copy.deepcopy(self.current);c['sources']['additive-ppundeoreo-74341']='https://example.invalid/changed'
  with self.assertRaisesRegex(AssertionError,'append-only ledger'):audit.verify_ledger(c,self.proposal)
 def test_coordinated_historical_mutation_cannot_pass(self):
  c=copy.deepcopy(self.current);later=audit.read(audit.ROOT/'docs/additive-ppundeoreo-proposed-ledger.json.gz')
  for ledger in [c,later['proposed_ledger']]:ledger['cases'][0]['judgments'][0]['reason']='changed old rationale'
  with self.assertRaisesRegex(AssertionError,'historical ledger prefix'):audit.verify_ledger(c,self.proposal,later)
 def test_coordinated_source_mutation_cannot_pass(self):
  c=copy.deepcopy(self.current);later=audit.read(audit.ROOT/'docs/additive-ppundeoreo-proposed-ledger.json.gz');key=next(iter(self.proposal['proposed_ledger']['sources']))
  for ledger in [c,later['proposed_ledger']]:ledger['sources'][key]='https://example.invalid/changed'
  with self.assertRaisesRegex(AssertionError,'historical source links'):audit.verify_ledger(c,self.proposal,later)
 def test_coordinated_later_count_mutation_cannot_pass(self):
  later=audit.read(audit.ROOT/'docs/additive-ppundeoreo-proposed-ledger.json.gz');later['new_counts']['required']+=1
  with self.assertRaisesRegex(AssertionError,'later judgments'):audit.verify_ledger(self.current,self.proposal,later)
 def test_coordinated_old_conditional_promotion_cannot_pass(self):
  c=copy.deepcopy(self.current);later=audit.read(audit.ROOT/'docs/additive-ppundeoreo-proposed-ledger.json.gz');ident=self.proposal['excluded_conditional_native_cases'][0]['id']
  c['cases'][-1]['id']=ident;later['proposed_ledger']['cases'][-1]['id']=ident;later['new_cases'][-1]['id']=ident
  with self.assertRaisesRegex(AssertionError,'historical conditional scope'):audit.verify_ledger(c,self.proposal,later)
if __name__=='__main__':unittest.main()
