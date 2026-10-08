"""Verify semantic corruption rejection after deliberately rebinding mutated capture bytes."""
import copy,json,tempfile,unittest
from pathlib import Path
import literary_question_geona_browser_audit as a
R=a.read(a.ROOT/'docs/literary-question-geona-main-browser-runtime.json.gz')
B=a.read(a.ROOT/'docs/literary-question-geona-main-browser.json.gz')
P=a.read(a.ROOT/'docs/literary-question-geona-complete-owner-preparation.json.gz')

def replace_at(value,path,fn):
    if not path:return fn(copy.deepcopy(value))
    result=value.copy();result[path[0]]=replace_at(value[path[0]],path[1:],fn);return result

class Controls(unittest.TestCase):
    def inspect_mutated(self,r,b):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'browser.json';p.write_text(json.dumps(b,ensure_ascii=False)+'\n')
            r=copy.deepcopy(r);r['browser_sha256']=a.sha(p.read_bytes())
            return a.inspect(r,b,P,browser_path=p)
    def reject_browser(self,path,fn):
        with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):
            self.inspect_mutated(R,replace_at(B,path,fn))
    def test_actual_complete_capture(self):self.assertEqual(self.inspect_mutated(R,B)['complete_native_entries'],241)
    def test_source_api_record_is_exact(self):self.reject_browser(['responses',0,'response','records',0,'surface'],lambda _: 'invented')
    def test_raw_dictionary_policy_is_not_forbidden(self):self.reject_browser(['modeJudgments',0,'present'],lambda _:False)
    def test_original_utf8_offsets(self):self.reject_browser(['exports',0,'records',0,'span','start'],lambda n:n+1)
    def test_missing_source_diagram(self):self.reject_browser(['diagrams'],lambda rows:rows[:-1])
    def test_label_source_title_is_bound(self):self.reject_browser(['diagrams',0,'title'],lambda _: '80970 only')
    def test_component_order_is_bound(self):self.reject_browser(['diagrams',0,'order'],lambda rows:list(reversed(rows)))
    def test_complete_native_fields_are_bound(self):self.reject_browser(['native',0,'response','entry','notes'],lambda rows:rows+['invented'])
    def test_source_panes_are_complete(self):self.reject_browser(['opened'],lambda rows:rows[:-1])
    def test_server_must_stop(self):
        r=copy.deepcopy(R);r['server_stopped']=False
        with self.assertRaises(AssertionError):self.inspect_mutated(r,B)
    def test_snapshot_files_cannot_lose_file(self):
        r=copy.deepcopy(R);r['snapshot_files'].pop(next(iter(r['snapshot_files'])))
        with self.assertRaises(AssertionError):self.inspect_mutated(r,B)

if __name__=='__main__':unittest.main()
