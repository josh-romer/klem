import copy,json,unittest
import literary_ri_prefinal_audit as a
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.inputs=a.inputs()
 def reject(self,index,change):
  inputs=copy.deepcopy(self.inputs);change(inputs[index])
  with self.assertRaises((AssertionError,KeyError,StopIteration,ValueError)):a.verify(*inputs)
 def test_complete_captures(self):self.assertEqual(a.verify(*self.inputs)['word_probes'],168)
 def test_original_reply_cannot_disappear(self):self.reject(0,lambda d:d['all_original_groups'].pop())
 def test_native_sense_cannot_disappear(self):self.reject(1,lambda d:d['complete_native_entries']['krdict:52612']['senses'].pop())
 def test_wrong_eat_homonym_cannot_replace_owner(self):self.reject(2,lambda d:d['cases'][0]['judgments'][0]['lemmas'].__setitem__(0,'드시다'))
 def test_original_span_cannot_change(self):self.reject(2,lambda d:d['cases'][0]['source_occurrence']['character_span'].__setitem__(0,0))
 def test_raw_hypothesis_cannot_become_global_ban(self):self.reject(4,lambda d:next(r for r in d['probes'] if r['case']=='literary-ri-prefinal-boundary-3-니' and r['mode']=='raw')['observations'][0].__setitem__('mode_verdict','forbidden'))
 def test_companion_boundaries_cannot_disappear(self):self.reject(6,lambda d:d['cases'].pop())
 def test_raw_spelling_constraints_cannot_be_added_silently(self):self.reject(5,lambda d:d['cases'].append(copy.deepcopy(self.inputs[6]['cases'][-1])))
 def test_stream_original_candidate_cannot_disappear(self):
  def change(d):
   run=d['streams'][0];rows=[json.loads(l) for l in run['jsonl'].splitlines()];row=next(r for r in rows if r.get('analysis'));row['analysis']['analyses'].pop();run['jsonl']=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows);run['sha256']=a.sha(run['jsonl'].encode())
  self.reject(4,change)
 def test_export_raw_hypothesis_cannot_be_hidden(self):
  def change(d):
   exported=next(r for r in d['exports'] if r['mode']=='raw' and r['encoding']=='NFC');record=next(r for r in exported['records'] if (r.get('analysis') or {}).get('normalized')=='듣으리니');j=next(c for c in self.inputs[2]['cases'] if c['surface']=='듣으리니')['judgments'][0];record['analysis']['analyses']=[p for p in record['analysis']['analyses'] if not a.match(p,j)]
  self.reject(7,change)
if __name__=='__main__':unittest.main()
