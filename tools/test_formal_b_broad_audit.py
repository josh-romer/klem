"""Reject corruption of actual full receipts, path ownership and new spacing."""
import copy,unittest
import formal_b_broad_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.evidence=audit.inputs()
 def reject(self,change,reason):
  values=copy.deepcopy(self.evidence);change(values)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*values)
 def test_actual_full_workloads(self):
  result=audit.inspect(*self.evidence)
  self.assertEqual((result['individual_paths'],result['spacing_observations'],result['native_entries']),(91,2,33))
 def test_missing_workload(self):self.reject(lambda v:v[0]['comparisons'].pop(),'all original workloads')
 def test_missing_individual_path(self):self.reject(lambda v:v[0]['individual_additions'].pop(),'individual additions')
 def test_missing_spacing_observation(self):self.reject(lambda v:v[0]['individual_spacing_additions'].pop(),'spacing observations')
 def test_changed_context(self):self.reject(lambda v:v[0]['comparisons'][3]['changed_frames'][0].update(complete_original_line='fabricated'),'original context')
 def test_old_path_removed(self):
  def change(v):
   f=v[0]['comparisons'][3]['changed_frames'][0];f['after']['analysis']['analyses'].remove(f['before']['analysis']['analyses'][0])
  self.reject(change,'old candidate preservation')
 def test_previous_stream_changed(self):self.reject(lambda v:v[0]['comparisons'][0].update(before_jsonl_sha256='0'*64),'previous stream')
 def test_unchanged_after_stream_changed(self):self.reject(lambda v:v[0]['comparisons'][0].update(after_jsonl_sha256='0'*64),'unchanged full stream hash')
 def test_original_source_changed(self):
  def change(v):
   source=v[0]['comparisons'][0]['source'];v[2]['sources'][source]['text']+='fabricated'
  self.reject(change,'original source text')
 def test_filter_flag_erased(self):self.reject(lambda v:v[0]['comparisons'][4]['commands'][1].remove('--dict-only'),'workload flags')
 def test_complete_owner_removed(self):self.reject(lambda v:v[4].pop(next(iter(v[4]))),'original Native owners')
 def test_native_summary_pos_rewritten(self):
  def change(v):
   f=v[0]['comparisons'][3]['changed_frames'][0];next(o for o in f['after']['dictionary']['lemmas'] if o['lemma']['text']=='같다')['entries'][0]['pos']='동사'
  self.reject(change,'exact Native owner summary')
 def test_observed_assessment_changed(self):self.reject(lambda v:v[0]['individual_additions'][0]['dictionary_assessment'].update(status='unknown'),'individual additions')
 def new_spacing(self,v):
  return next(f for r in v[0]['comparisons'] for f in r['changed_frames'] if f['added_spacing_options'])['after']['spacing']['alternatives'][-1]
 def test_spacing_boundary_changed(self):
  self.reject(lambda v:self.new_spacing(v)['inserted_at'].__setitem__(0,0),'new spacing byte boundaries')
 def test_spacing_segment_source_changed(self):
  self.reject(lambda v:self.new_spacing(v)['records'][1]['span'].update(end=749640),'segment source bytes')
 def test_independent_segment_assessment_changed(self):
  self.reject(lambda v:v[0]['independent_spacing_replay']['답디까']['dictionary']['readings'][-1].update(status='incompatible'),'independent assessment')
 def test_regression_context_rewritten(self):
  self.reject(lambda v:v[5]['raw_changed_frames'][0].update(complete_original_line='fabricated'),'novel frame regression')
 def test_context_promoted_to_gold(self):
  self.reject(lambda v:v[0]['individual_spacing_additions'][0].update(contextual_verdict='required'),'spacing observations')
if __name__=='__main__':unittest.main()
