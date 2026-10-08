import copy,importlib.util,json,unittest
from pathlib import Path
import os
import possessive_bound_noun_runtime as runtime
root=runtime.ROOT
closure=Path(os.environ.get('KLEM_POSSESSIVE_CLOSURE',root/'docs/possessive-bound-noun-native-closure.json.gz'))
fixture=runtime.read(Path(os.environ.get('KLEM_POSSESSIVE_FIXTURE',root/'tests/fixtures/possessive-bound-noun-cases.json')))
report=runtime.read(Path(os.environ.get('KLEM_POSSESSIVE_RUNTIME',root/'docs/possessive-bound-noun-installed-runtime.json.gz')))
class Integrity(unittest.TestCase):
 def reject(self,change):
  mutated=copy.deepcopy(report);change(mutated)
  with self.assertRaises((AssertionError,ValueError,KeyError)):runtime.verify(mutated,fixture,closure)
 def test_observations_pass_without_claiming_unmet_requirement_complete(self):
  result=runtime.verify(report,fixture,closure)
  self.assertTrue(result['observations_verified']);self.assertFalse(result['finite_requirements_passed']);self.assertEqual(result['unmet_requirements'],['surname-teacher'])
 def test_hidden_unmet(self):self.reject(lambda r:r.update(unmet_requirements=[]))
 def test_full_completion_claim(self):self.reject(lambda r:r.update(full_coverage_complete=True))
 def test_missing_run(self):self.reject(lambda r:r['runs'].pop())
 def test_duplicate_run(self):self.reject(lambda r:r['runs'].append(copy.deepcopy(r['runs'][0])))
 def test_changed_fixture(self):self.reject(lambda r:r['fixture']['cases'].pop())
 def test_changed_closure_hash(self):self.reject(lambda r:r.update(closure_sha256='0'*64))
 def test_changed_native_entry(self):self.reject(lambda r:r['native']['krdict:62835'].update(pos='명사'))
 def test_changed_observation(self):self.reject(lambda r:r['observations'][0].update(actual=[]))
 def test_word_candidate_loss(self):
  def change(r):
   frame=next(f for f in r['runs'][0]['after'] if (f.get('analysis') or {}).get('analyses'))
   frame['analysis']['analyses']=[]
  self.reject(change)
 def test_prior_option_loss(self):
  def change(r):
   frame=next(f for f in r['runs'][0]['baseline_spacing'] if f.get('spacing',{}).get('alternatives'))
   frame['spacing']['alternatives'].append({'spaced':'unretained original option'})
  self.reject(change)
 def test_changed_source_span(self):
  def change(r):
   frame=next(f for f in r['runs'][0]['after'] if any(h.get('rule')==runtime.RULE for h in f.get('spacing',{}).get('alternatives',[])))
   h=next(h for h in frame['spacing']['alternatives'] if h.get('rule')==runtime.RULE);h['records'][0]['span']['start']+=1
  self.reject(change)
if __name__=='__main__':unittest.main()
