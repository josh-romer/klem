"""Reject corruption of novel additions, original contexts and complete Native owners."""
import copy,unittest
import explanatory_se_broad_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.evidence=audit.inputs()
 def reject(self,change,reason):
  values=copy.deepcopy(self.evidence);change(values)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*values)
 def test_actual_full_workloads(self):
  result=audit.inspect(*self.evidence)
  self.assertEqual((result['individual_paths'],result['spacing_observations'],result['native_entries']),(655,12,128))
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
   f=v[0]['comparisons'][3]['changed_frames'][0];next(o for o in f['after']['dictionary']['lemmas'] if o['entries'] and o not in f['before']['dictionary']['lemmas'])['entries'][0]['pos']='fabricated'
  self.reject(change,'exact Native owner summary')
 def test_observed_assessment_changed(self):self.reject(lambda v:v[0]['individual_additions'][0]['dictionary_assessment'].update(status='compatible' if v[0]['individual_additions'][0]['dictionary_assessment']['status']!='compatible' else 'incompatible'),'individual additions')
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
   next(p for p in f['after']['analysis']['analyses'] if p not in f['before']['analysis']['analyses'])['rules'][:]=[r for r in next(p for p in f['after']['analysis']['analyses'] if p not in f['before']['analysis']['analyses'])['rules'] if r not in ['ending.explanatory_se','particle.familiar_gryeo']]
  self.reject(change,'new rule attribution')
 def new_option(self,values):
  for run in values[0]['comparisons']:
   for frame in run['changed_frames']:
    if 'spacing' not in frame['after']:continue
    keys=lambda h:(h.get('rule'),h['spaced'],tuple(h['inserted_at']))
    old={keys(h) for h in frame['before']['spacing']['alternatives']}
    for hypothesis in frame['after']['spacing']['alternatives']:
     if keys(hypothesis) not in old:return hypothesis
  raise AssertionError('missing new spacing capture')
 def test_new_spacing_segment_original_bytes(self):
  def change(v):
   span=self.new_option(v)['records'][0]['span'];span['end']+=3
  self.reject(change,'segment source bytes')
 def test_independent_spacing_assessment(self):
  def change(v):
   segment=self.new_option(v)['records'][0];replay=v[0]['independent_spacing_replay'][segment['surface']];index=replay['analyses'].index(segment['analysis']['analyses'][0]);reading=replay['dictionary']['readings'][index]
   reading['status']='incompatible' if reading['status']!='incompatible' else 'compatible'
  self.reject(change,'independent assessment')
 def test_missing_spacing_observation(self):self.reject(lambda v:v[0]['individual_spacing_additions'].pop(),'individual spacing observations')
 def test_coordinated_native_original_rewrite(self):
  def change(v):
   lexical=v[3]['LexicalResource']['Lexicon']['LexicalEntry'][0];lexical['invented']='coordinated'
  self.reject(change,'pinned original Native fields')
if __name__=='__main__':unittest.main()

