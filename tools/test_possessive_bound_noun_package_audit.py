import copy,importlib.util,unittest
from pathlib import Path
import os
import possessive_bound_noun_package_audit as audit
root=audit.ROOT
receipt=audit.read(Path(os.environ.get('KLEM_POSSESSIVE_PACKAGE',root/'docs/possessive-bound-noun-nix.json.gz')))
sources=audit.read(Path(os.environ.get('KLEM_POSSESSIVE_SOURCES',root/'docs/possessive-bound-noun-installed-sources.json.gz')))
adapter=audit.read(Path(os.environ.get('KLEM_POSSESSIVE_ADAPTER',root/'docs/possessive-bound-noun-installed-adapter.json.gz')))
corpus=audit.read(root/'docs/literary-question-geona-prototype-corpora.json.gz')
class Integrity(unittest.TestCase):
 def reject_source(self,change):
  mutated=copy.deepcopy(sources);change(mutated)
  with self.assertRaises((AssertionError,KeyError,ValueError)):audit.source_audit(mutated,receipt)
 def test_source_and_original_adapter_rows(self):
  self.assertEqual(audit.source_audit(sources,receipt)['source_inputs'],977)
  self.assertEqual(audit.adapter_audit(adapter,receipt,corpus)['actual_original_annotated_rows'],66570)
 def test_source_text_change(self):self.reject_source(lambda p:next(iter(p['updates'].values())).update(after_text='invented source'))
 def test_nar_change(self):self.reject_source(lambda p:p['profiles']['klem'].update(nar_sha256='0'*64))
 def test_wrong_profile(self):self.reject_source(lambda p:p['profiles']['klem'].update(source='/nix/store/other-source'))
 def test_missing_input(self):self.reject_source(lambda p:p['snapshot_files'].pop(next(iter(p['snapshot_files']))))
 def test_false_dump(self):self.reject_source(lambda p:p['profiles']['klem'].update(actual_dump_verified=False))
 def test_hidden_gold_rows(self):
  mutated=copy.deepcopy(adapter);mutated['runs'][0]['rows']-=1
  with self.assertRaises(AssertionError):audit.adapter_audit(mutated,receipt,corpus)
 def test_full_precision_claim(self):
  mutated=copy.deepcopy(adapter);mutated['contextual_verdict']='correct'
  with self.assertRaises(AssertionError):audit.adapter_audit(mutated,receipt,corpus)
if __name__=='__main__':unittest.main()
