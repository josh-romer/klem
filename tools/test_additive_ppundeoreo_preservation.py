"""Mutate real completed captures; keep digest rebinding separate from semantic checks."""
import copy,importlib.util,os,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
import additive_ppundeoreo_preservation_audit as a
PHASE=os.environ.get('KLEM_PPUN_PHASE','isolated')
B,C,PB,PC,PH=a.inputs(phase=PHASE)
def replace_at(value,path,fn):
 if not path:return fn(copy.deepcopy(value))
 result=value.copy();result[path[0]]=replace_at(value[path[0]],path[1:],fn);return result
class Controls(unittest.TestCase):
 def test_actual_complete_captures_pass(self):self.assertEqual(a.inspect(B,C,PB,PC,PH,phase=PHASE)['broad_frames'],1128312)
 def reject_broad(self,path,fn):
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError)):a.inspect(replace_at(B,path,fn),C,PB,PC,PH,phase=PHASE)
 def reject_cohort(self,path,fn):
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError)):a.inspect(B,replace_at(C,path,fn),PB,PC,PH,phase=PHASE)
 def test_offline_audit_root_can_move(self):
  with tempfile.TemporaryDirectory() as directory:
   relocated=Path(directory);(relocated/'docs').symlink_to(a.ROOT/'docs',target_is_directory=True)
   with patch.object(a,'ROOT',relocated):self.assertEqual(a.inspect(B,C,PB,PC,PH,phase=PHASE)['broad_frames'],1128312)
 def test_all_eight_streams_required(self):self.reject_broad(['comparisons'],lambda rows:rows[:-1])
 def test_actual_complete_frame_count_required(self):self.reject_broad(['comparisons',0,'records'],lambda n:n-1)
 def test_prior_digest_bound(self):self.reject_broad(['comparisons',0,'before_jsonl_sha256'],lambda _:'0'*64)
 def test_current_digest_bound(self):self.reject_broad(['comparisons',0,'after_jsonl_sha256'],lambda _:'0'*64)
 def test_actual_dictionary_filter_command_bound(self):self.reject_broad(['comparisons',0,'commands',1],lambda command:command+['--dict-compatible'])
 def test_failed_process_cannot_pass(self):self.reject_broad(['comparisons',0,'exit_codes'],lambda _:[0,1])
 def test_no_precision_claim(self):self.reject_broad(['contextual_verdict'],lambda _:'correct')
 def test_historical_cohort_required(self):self.reject_cohort(['cohorts'],lambda rows:rows[:-1])
 def test_missing_original_word_rejected(self):
  self.reject_cohort(['cohorts',0,'after_words'],lambda words:{k:v for k,v in words.items() if k!=next(iter(words))})
 def test_changed_original_lemma_rejected(self):
  word=next(iter(C['cohorts'][0]['after_words']))
  self.reject_cohort(['cohorts',0,'after_words',word,'analyses'],lambda _ : [])
 def test_current_word_digest_rederived(self):self.reject_cohort(['cohorts',0,'after_word_sha256'],lambda _:'0'*64)
if __name__=='__main__':unittest.main()
