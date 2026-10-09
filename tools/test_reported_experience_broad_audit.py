"""Reject corruption of novel additions, original contexts and complete Native owners."""
import copy,unittest
import reported_experience_broad_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.evidence=audit.inputs()
 def reject(self,change,reason):
  values=copy.deepcopy(self.evidence);change(values)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*values)
 def test_actual_full_workloads(self):
  result=audit.inspect(*self.evidence)
  self.assertEqual((result['individual_paths'],result['spacing_observations'],result['native_entries']),(16,0,2))
 def test_missing_workload(self):self.reject(lambda v:v[0]['comparisons'].pop(),'all original workloads')
 def test_missing_individual_path(self):self.reject(lambda v:v[0]['individual_additions'].pop(),'individual additions')
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
   f=v[0]['comparisons'][3]['changed_frames'][0];next(o for o in f['after']['dictionary']['lemmas'] if o['lemma']['text']=='벌다')['entries'][0]['pos']='형용사'
  self.reject(change,'exact Native owner summary')
 def test_observed_assessment_changed(self):self.reject(lambda v:v[0]['individual_additions'][0]['dictionary_assessment'].update(status='incompatible'),'individual additions')
 def test_regression_context_rewritten(self):self.reject(lambda v:v[5]['raw_changed_frames'][0].update(complete_original_line='fabricated'),'novel frame regression')
 def test_context_promoted_to_gold(self):self.reject(lambda v:v[0]['individual_additions'][0].update(contextual_verdict='required'),'individual additions')
 def test_previous_spacing_boundary_removed(self):
  def change(v):
   frame=next(f for r in v[0]['comparisons'] if 'spacing' in r['mode'] for f in r['changed_frames'] if f['before']['spacing']['alternatives'])
   frame['after']['spacing']['alternatives'].pop(0)
  self.reject(change,'old spacing boundary preservation')
 def test_new_rule_attribution_erased(self):
  def change(v):
   f=v[0]['comparisons'][3]['changed_frames'][0]
   next(p for p in f['after']['analysis']['analyses'] if p not in f['before']['analysis']['analyses'])['rules'].remove('ending.reported_experience')
  self.reject(change,'new rule attribution')
if __name__=='__main__':unittest.main()
