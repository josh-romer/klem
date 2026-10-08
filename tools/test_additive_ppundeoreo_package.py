"""Reject semantic release corruption after validating actual installed positive evidence."""
import copy,json,unittest
import additive_ppundeoreo_package as a
P,C,A,W,B=a.inputs()
class Controls(unittest.TestCase):
 def inspect_browser(self,web,browser):
  web=copy.deepcopy(web);web['browser_sha256']=a.sha(json.dumps(browser,ensure_ascii=False,indent=2).encode()+b'\n');return a.inspect(P,C,A,web,browser)
 def reject(self,index,fn):
  reports=[P,C,A,W,B];reports[index]=copy.deepcopy(reports[index]);fn(reports[index])
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):a.inspect(*reports)
 def reject_browser(self,fn):
  b=copy.deepcopy(B);fn(b)
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):self.inspect_browser(W,b)
 def test_actual_complete_installed_capture(self):self.assertEqual(a.inspect(P,C,A,W,B)['source_inputs'],964)
 def test_main_cli_cannot_replace_installed_cli(self):self.reject(1,lambda r:r.__setitem__('cli','/tmp/klem-additive-ppundeoreo-main-cli'))
 def test_source_snapshot_cannot_lose_file(self):self.reject(1,lambda r:r['snapshot_files'].pop(next(iter(r['snapshot_files']))))
 def test_finite_mode_cannot_disappear(self):self.reject(1,lambda r:r['finite_runs'].pop())
 def test_complete_novel_output_is_bound(self):self.reject(1,lambda r:r['broad'][0].__setitem__('output_sha256','0'*64))
 def test_historical_word_digest_is_bound(self):self.reject(1,lambda r:r['words'][1].__setitem__('word_sha256','0'*64))
 def test_adapter_original_gold_is_bound(self):
  def mutate(r):
   run=r['runs'][0];rows=list(map(json.loads,run['jsonl'].splitlines()));rows[1]['expected']=[['invented']];run['jsonl']=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows);run['sha256']=a.sha(run['jsonl'].encode())
  self.reject(2,mutate)
 def test_owned_server_must_stop(self):self.reject(3,lambda r:r.__setitem__('server_stopped',False))
 def test_launcher_command_is_exact(self):
  def mutate(r):
   r['launcher_text']=r['launcher_text'].replace(r['server'],'/tmp/wrong-server');r['launcher_sha256']=a.sha(r['launcher_text'].encode());r['frozen_inputs'][r['launcher']]=r['launcher_sha256']
  self.reject(3,mutate)
 def test_served_asset_is_exact(self):self.reject(3,lambda r:r['asset_checks'][0].__setitem__('sha256','0'*64))
 def test_native_fields_are_exact(self):self.reject_browser(lambda b:b['native'][0]['response']['entry']['notes'].append('invented'))
 def test_label_source_id_is_exact(self):self.reject_browser(lambda b:b['diagrams'][0].__setitem__('title','74341 only'))
 def test_component_order_is_exact(self):self.reject_browser(lambda b:b['diagrams'][0]['order'].reverse())
 def test_export_original_offsets_are_exact(self):self.reject_browser(lambda b:b['exports'][0]['records'][0]['span'].__setitem__('start',1))
 def test_source_api_elapsed_time_is_valid(self):self.reject_browser(lambda b:b['responses'][0]['response'].__setitem__('elapsed_ms',-1))
if __name__=='__main__':unittest.main()
