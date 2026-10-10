"""Reject missing or altered complete installed-package evidence."""
import unittest
from unittest.mock import patch
import formal_b_installed_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.evidence=audit.inputs()
 def test_complete_installed_capture(self):self.assertEqual(audit.inspect(*self.evidence)['finite_frames'],12396)
 def reject(self,obj,updates,reason):
  with patch.dict(obj,updates):
   with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*self.evidence)
 def test_complete_source_profile(self):
  profiles=self.evidence[0]['profiles'];self.reject(profiles['klem'],{'files':{}},'complete source files')
 def test_source_derivation_identity(self):self.reject(self.evidence[0]['profiles']['klem'],{'source':'/nix/store/fabricated'},'package source identity')
 def test_one_broad_workload(self):self.reject(self.evidence[1],{'runs':self.evidence[1]['runs'][:-1]},'complete broad workloads')
 def test_complete_broad_output(self):self.reject(self.evidence[1]['runs'][0],{'actual_jsonl_sha256':'0'*64},'complete installed broad output')
 def test_original_cohort_word(self):
  capture=self.evidence[2]['runs'][0]['captures'][1];words=dict(capture['words']);words.pop(next(iter(words)))
  self.reject(capture,{'words':words,'word_sha256':audit.sha(audit.json.dumps(words,ensure_ascii=False,sort_keys=True).encode())},'every complete original word')
 def test_annotated_output(self):self.reject(self.evidence[3]['runs'][0],{'jsonl':'fabricated\n'},'all complete original annotated outputs')
 def test_missing_unicode_cache_stream(self):self.reject(self.evidence[4],{'runs':self.evidence[4]['runs'][:-1]},'complete Unicode/filter/cache streams')
 def test_finite_input(self):self.reject(self.evidence[4]['runs'][0],{'input_sha256':'0'*64},'complete finite source input')
 def test_browser_server_shutdown(self):self.reject(self.evidence[6],{'server_stopped':False},'actual installed browser runtime')
 def test_browser_diagram_missing(self):self.reject(self.evidence[5],{'diagrams':self.evidence[5]['diagrams'][:-1]},'complete installed browser captures')
if __name__=='__main__':unittest.main()
