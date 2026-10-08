"""Verify semantic corruption rejection after deliberately rebinding mutated capture bytes."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import importlib.util
import additive_ppundeoreo_browser_audit as a
PHASE=os.environ.get('KLEM_PPUN_PHASE','isolated')
PREFIX='main' if PHASE=='main' else 'current'
R=a.read(a.ROOT/'docs'/('additive-ppundeoreo-'+PREFIX+'-browser-runtime.json.gz'))
B=a.read(a.ROOT/'docs'/('additive-ppundeoreo-'+PREFIX+'-browser.json.gz'))
P=a.read(a.ROOT/'docs/additive-ppundeoreo-owner-closure.json.gz')

def replace_at(value,path,fn):
    if not path:return fn(copy.deepcopy(value))
    result=value.copy();result[path[0]]=replace_at(value[path[0]],path[1:],fn);return result

class Controls(unittest.TestCase):
    def inspect_mutated(self,r,b):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'browser.json';p.write_text(json.dumps(b,ensure_ascii=False)+'\n')
            r=copy.deepcopy(r);r['browser_sha256']=a.sha(p.read_bytes())
            return a.inspect(r,b,P,browser_path=p,phase=PHASE)
    def reject_browser(self,path,fn):
        with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):
            self.inspect_mutated(R,replace_at(B,path,fn))
    def test_selected_phase_is_bound(self):
        self.assertEqual(self.inspect_mutated(R,B)['phase'],PHASE)
        opposite='isolated' if PHASE=='main' else 'main'
        with self.assertRaises((AssertionError,KeyError,StopIteration)):
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory)/'browser.json';p.write_text(json.dumps(B,ensure_ascii=False)+'\n')
                r=copy.deepcopy(R);r['browser_sha256']=a.sha(p.read_bytes())
                a.inspect(r,B,P,browser_path=p,phase=opposite)
    def test_actual_complete_capture(self):self.assertEqual(self.inspect_mutated(R,B)['complete_native_entries'],62)
    def test_audit_root_can_move_without_rewriting_frozen_producer_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ['docs','tools','tests','web']:
                (root/name).symlink_to(a.ROOT/name,target_is_directory=True)
            with patch.object(a,'ROOT',root):
                self.assertEqual(self.inspect_mutated(R,B)['complete_native_entries'],62)
    def test_source_api_record_is_exact(self):self.reject_browser(['responses',0,'response','records',0,'surface'],lambda _: 'invented')
    def test_raw_dictionary_policy_is_not_forbidden(self):self.reject_browser(['modeJudgments',0,'present'],lambda _:False)
    def test_original_utf8_offsets(self):self.reject_browser(['exports',0,'records',0,'span','start'],lambda n:n+1)
    def test_missing_source_diagram(self):self.reject_browser(['diagrams'],lambda rows:rows[:-1])
    def test_label_source_title_is_bound(self):self.reject_browser(['diagrams',0,'title'],lambda _: '74341 only')
    def test_component_order_is_bound(self):self.reject_browser(['diagrams',0,'order'],lambda rows:list(reversed(rows)))
    def test_complete_native_fields_are_bound(self):self.reject_browser(['native',0,'response','entry','notes'],lambda rows:rows+['invented'])
    def test_source_panes_are_complete(self):self.reject_browser(['opened'],lambda rows:rows[:-1])
    def test_server_must_stop(self):
        r=copy.deepcopy(R);r['server_stopped']=False
        with self.assertRaises(AssertionError):self.inspect_mutated(r,B)
    def test_served_asset_digest_is_bound(self):
        r=copy.deepcopy(R);r['served_asset_checks'][0]['sha256']='0'*64
        with self.assertRaises(AssertionError):self.inspect_mutated(r,B)
    def test_served_assets_cannot_disappear(self):
        r=copy.deepcopy(R);r['served_asset_checks'].pop()
        with self.assertRaises(AssertionError):self.inspect_mutated(r,B)
    def test_snapshot_files_cannot_lose_file(self):
        r=copy.deepcopy(R);r['snapshot_files'].pop(next(iter(r['snapshot_files'])))
        with self.assertRaises(AssertionError):self.inspect_mutated(r,B)

if __name__=='__main__':unittest.main()
