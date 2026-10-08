"""Negative controls for captured real boundary evidence; not language judgments."""
import copy,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'tools/bound_noun_spacing_runtime.py';spec=importlib.util.spec_from_file_location('bound_runtime',p);runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
closure=ROOT/'docs/bound-noun-spacing-native-closure.json.gz';fixture=runtime.read(ROOT/'tests/fixtures/bound-noun-spacing-cases.json');capture=runtime.read(ROOT/'docs/bound-noun-spacing-installed-runtime.json.gz')
def hypothesis(r):
 return next(h for row in r['runs'][0]['after'] for h in row.get('spacing',{}).get('alternatives',[]) if h.get('rule')==runtime.RULE and h.get('joined_contexts'))
class Controls(unittest.TestCase):
 def rejected(self,mutate):
  r=copy.deepcopy(capture);mutate(r)
  with self.assertRaises((AssertionError,KeyError,ValueError,IndexError,StopIteration)):
   runtime.verify(r,fixture,closure)
 def test_unmodified_capture(self):
  result=runtime.verify(capture,fixture,closure);self.assertEqual(result['observations'],900);self.assertFalse(result['full_coverage_complete'])
 def test_hidden_original(self):self.rejected(lambda r:r['original_unmet_requirement'].update(required_space='먹어 준 것은'))
 def test_completion_claim(self):self.rejected(lambda r:r.update(full_coverage_complete=True))
 def test_changed_requirement(self):self.rejected(lambda r:r['fixture']['cases'][0].update(required_spaces=[]))
 def test_missing_unicode_run(self):self.rejected(lambda r:r['runs'].pop())
 def test_duplicate_run(self):self.rejected(lambda r:r['runs'].__setitem__(1,copy.deepcopy(r['runs'][0])))
 def test_changed_observation(self):self.rejected(lambda r:r['observations'][0].update(case_id='relabeled'))
 def test_changed_raw_candidate(self):self.rejected(lambda r:next(row for row in r['runs'][0]['before'] if row.get('analysis'))['analysis']['analyses'].append({'invented':True}))
 def test_missing_prior_option(self):
  def mutate(r):
   row=next(row for row in r['runs'][0]['baseline_spacing'] if row.get('spacing',{}).get('alternatives'));row['spacing']['alternatives'].append({'spaced':'invented prior'})
  self.rejected(mutate)
 def test_wrong_surface_span(self):self.rejected(lambda r:hypothesis(r)['records'][0]['span'].update(start=0))
 def test_context_includes_noun(self):self.rejected(lambda r:hypothesis(r)['joined_contexts'][0]['span'].update(end=hypothesis(r)['records'][-1]['span']['end']))
 def test_context_stops_early(self):self.rejected(lambda r:hypothesis(r)['joined_contexts'][0]['span'].update(end=hypothesis(r)['joined_contexts'][0]['span']['end']-3))
 def test_duplicate_context_span(self):self.rejected(lambda r:hypothesis(r)['joined_contexts'].append(copy.deepcopy(hypothesis(r)['joined_contexts'][0])))
 def test_missing_independent_native(self):self.rejected(lambda r:hypothesis(r)['records'][-1]['dictionary']['lemmas'].clear())
 def test_wrong_ordered_layout(self):self.rejected(lambda r:hypothesis(r)['records'][0]['breakdowns'][0].clear())
 def test_missing_native_endpoint(self):self.rejected(lambda r:r['native'].pop('krdict:15615'))
 def test_changed_api_metadata(self):self.rejected(lambda r:r['api']['NFC']['rules'].pop(runtime.RULE))
 def test_changed_api_records(self):self.rejected(lambda r:r['api']['NFC']['records'].pop())
if __name__=='__main__':unittest.main()
