"""Corruption controls for original gold and independently derived recovery."""
import copy,unittest
import giroseo_corpora_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.evidence=audit.inputs()
 def reject(self,fn,reason):
  values=copy.deepcopy(self.evidence);fn(values)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*values)
 def rows(self,v,fn):
  run=v[0]['runs'][0];rows=[audit.json.loads(x) for x in run['jsonl'].splitlines()];fn(rows)
  run['jsonl']=''.join(audit.json.dumps(r,ensure_ascii=False)+'\n' for r in rows);run['stdout_sha256']=audit.sha(run['jsonl'].encode())
 def test_complete_actual_rows(self):self.assertEqual(audit.inspect(*self.evidence)['original_gold_rows'],66570)
 def test_missing_partition(self):self.reject(lambda v:v[0]['runs'].pop(),'complete gold partitions')
 def test_missing_row_after_rehash(self):self.reject(lambda v:self.rows(v,lambda rows:rows.pop()),'all original gold rows')
 def test_original_gold_rewritten(self):self.reject(lambda v:self.rows(v,lambda rows:rows[1].update(expected=[['invented']])),'original gold identity')
 def test_recovery_rederived(self):self.reject(lambda v:self.rows(v,lambda rows:rows[1].update(recovered=999)),'derived gold recovery')
 def test_candidates_rederived(self):self.reject(lambda v:self.rows(v,lambda rows:rows[0].update(mean_candidates=0)),'derived candidate statistics')
 def test_capture_digest_bound(self):self.reject(lambda v:v[0]['runs'][0].update(stdout_sha256='0'*64),'capture digest')
 def test_source_text_bound(self):self.reject(lambda v:v[2]['corpora'][0].update(original_source_text='fabricated'),'original source text')
 def test_actual_command_bound(self):self.reject(lambda v:v[0]['runs'][0]['command'].append('--invented'),'actual adapter command')
 def test_invented_changed_row(self):self.reject(lambda v:v[0]['individual_changed_rows'].append({'id':'invented'}),'unchanged row accounting')
if __name__=='__main__':unittest.main()
