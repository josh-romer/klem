import copy,importlib.util,unittest
import literary_future_kko_adapter_audit as a
R=a.read(a.ROOT/'docs/literary-question-go-main-adapter.json.gz');C=a.read(a.ROOT/'docs/literary-future-kko-prototype-corpora.json.gz')
class Controls(unittest.TestCase):
 def reject(self,fn):
  r=copy.deepcopy(R);fn(r)
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):a.inspect(r,C)
 def mutate_rows(self,r,fn):
  run=r['runs'][0];rows=list(map(a.json.loads,run['jsonl'].splitlines()));fn(rows);run['jsonl']=''.join(a.json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows);run['sha256']=a.sha(run['jsonl'].encode());run['summary']=rows[0]
 def test_complete_partition_cannot_disappear(self):self.reject(lambda r:r['runs'].pop())
 def test_one_original_gold_row_cannot_disappear(self):self.reject(lambda r:self.mutate_rows(r,lambda rows:rows.pop()))
 def test_original_gold_lemma_group_is_bound(self):self.reject(lambda r:self.mutate_rows(r,lambda rows:rows[1].__setitem__('expected',[['invented']])) )
 def test_recovery_is_rederived(self):self.reject(lambda r:self.mutate_rows(r,lambda rows:rows[1].__setitem__('recovered',999)))
 def test_candidate_statistics_are_independently_derived(self):self.reject(lambda r:self.mutate_rows(r,lambda rows:rows[0].__setitem__('mean_candidates',0)))
 def test_actual_adapter_identity_is_bound(self):self.reject(lambda r:r.__setitem__('adapter_sha256','0'*64))
 def test_no_precision_claim_from_gold_recovery(self):self.reject(lambda r:r.__setitem__('contextual_verdict','correct'))
if __name__=='__main__':unittest.main()
