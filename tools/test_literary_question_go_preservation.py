"""Capture corruption controls, including explicit prior-spacing conservation."""
import copy,importlib.util,unittest
import literary_question_go_preservation as a
B=a.read(a.ROOT/'docs/literary-question-go-prototype-broad.json.gz');C=a.read(a.ROOT/'docs/literary-question-go-prototype-corpora.json.gz')
def replace_at(obj,path,fn):
 if not path:return fn(copy.deepcopy(obj))
 result=obj.copy();result[path[0]]=replace_at(obj[path[0]],path[1:],fn);return result
class Controls(unittest.TestCase):
 def reject_broad(self,path,fn):
  b=replace_at(B,path,fn)
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError)):a.inspect(b,C)
 def reject_corpus(self,path,fn):
  c=replace_at(C,path,fn)
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError)):a.inspect(B,c)
 def test_missing_word_observation(self):self.reject_broad(['individual_additions'],lambda x:x[:-1])
 def test_missing_spacing_observation(self):self.reject_broad(['individual_spacing_additions'],lambda x:x[:-1])
 def test_spacing_id_is_rederived(self):self.reject_broad(['individual_spacing_additions',0,'id'],lambda x:x+'invented')
 def test_spacing_is_not_certified(self):self.reject_broad(['individual_spacing_additions',0,'structural_verdict'],lambda x:'required')
 def test_spacing_native_entry_status_is_bound(self):
  self.reject_broad(['individual_spacing_additions',0,'hypothesis','records',1,'dictionary','readings',0,'status'],lambda x:'incompatible')
 def test_spacing_original_span_is_bound(self):
  self.reject_broad(['individual_spacing_additions',0,'hypothesis','records',1,'span','start'],lambda x:x+1)
 def test_prior_spacing_alternative_loss_is_rejected(self):
  # A controlled injection using an actually captured alternative makes the
  # conservation branch observable; this is not an upstream source judgment.
  b=copy.deepcopy(B);obs=b['individual_spacing_additions'][0];run=next(r for r in b['comparisons'] if r['mode']==obs['mode']);delta=next(r for r in run['changed_frames'] if r['record']==obs['record']);delta['before']['spacing']['alternatives']=[copy.deepcopy(obs['hypothesis'])];delta['after']['spacing']['alternatives']=[]
  with self.assertRaises(AssertionError):a.inspect(b,C)
 def test_existing_segment_reading_loss_is_rejected(self):
  b=copy.deepcopy(B);obs=b['individual_spacing_additions'][0];run=next(r for r in b['comparisons'] if r['mode']==obs['mode']);delta=next(r for r in run['changed_frames'] if r['record']==obs['record']);delta['before']['spacing']['alternatives']=[copy.deepcopy(obs['hypothesis'])];delta['after']['spacing']['alternatives'][0]['records'][1]['analysis']['analyses']=[]
  with self.assertRaises(AssertionError):a.inspect(b,C)
 def test_new_paths_keep_individual_ids(self):self.reject_corpus(['candidate_changes',0,'id'],lambda x:x+'invented')
 def test_new_paths_keep_original_context(self):self.reject_corpus(['candidate_changes',0,'occurrences'],lambda x:[])
 def test_new_paths_are_not_certified(self):self.reject_corpus(['candidate_changes',0,'structural_verdict'],lambda x:'required')
 def test_candidate_count_change_is_not_a_gold_gain(self):
  self.reject_corpus(['corpora',0,'comparisons',0,'after','recovered'],lambda x:x+1)
 def test_original_gold_rows_are_immutable(self):self.reject_corpus(['corpora',0,'original_converted_rows',0,'surface'],lambda x:x+'고')
 def test_original_baseline_is_not_the_new_binary(self):self.reject_broad(['before_cli_sha256'],lambda x:B['cli_sha256'])
if __name__=='__main__':unittest.main()
