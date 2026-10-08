"""Negative controls for actual installed source and annotated-row evidence."""
import copy,importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'tools/bound_noun_spacing_package_audit.py';spec=importlib.util.spec_from_file_location('audit',p);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
receipt=a.read(ROOT/'docs/bound-noun-spacing-nix.json.gz');proof=a.read(ROOT/'docs/bound-noun-spacing-installed-sources.json.gz');adapter=a.read(ROOT/'docs/bound-noun-spacing-installed-adapter.json.gz');corpus=a.read(a.ROOT/'docs/literary-question-geona-prototype-corpora.json.gz')
class Sources(unittest.TestCase):
 def bad(self,mutate):
  q=copy.deepcopy(proof);mutate(q)
  with self.assertRaises((AssertionError,KeyError,ValueError)):a.source_audit(q,receipt)
 def test_original(self):self.assertEqual(a.source_audit(proof,receipt)['source_inputs'],973)
 def test_compressed_receipt_preserves_captured_identity(self):self.assertEqual(a.sha(a.receipt_bytes(ROOT/'docs/bound-noun-spacing-nix.json.gz')),proof['receipt_sha256'])
 def test_missing_delta(self):self.bad(lambda q:q['updates'].pop('src/spacing/bound_noun.rs'))
 def test_changed_before_hash(self):self.bad(lambda q:q['updates']['src/spacing.rs'].update(before_sha256='0'*64))
 def test_missing_snapshot(self):self.bad(lambda q:q['snapshot_files'].pop('src/spacing/bound_noun.rs'))
 def test_changed_byte_count(self):self.bad(lambda q:q['snapshot_files']['src/spacing.rs'].update(bytes=1))
 def test_changed_baseline(self):self.bad(lambda q:q['baseline'].update(proof_sha256='0'*64))
 def test_missing_profile(self):self.bad(lambda q:q['profiles'].pop('web-assets'))
 def test_swapped_package_role(self):self.bad(lambda q:q['profiles']['klem'].update(package=q['profiles']['corpus-adapter']['package']))
 def test_changed_nar_hash(self):self.bad(lambda q:q['profiles']['klem'].update(nar_sha256='0'*64))
 def test_changed_nar_command(self):self.bad(lambda q:q['profiles']['klem'].update(nar_command=['invented']))
 def test_missing_native_fixture(self):self.bad(lambda q:q['profiles']['klem']['files'].pop('tests/fixtures/bound-noun-spacing-native.json'))
 def test_changed_executable(self):self.bad(lambda q:q['profiles']['klem']['files']['src/spacing.rs'].update(executable=True))
class Adapter(unittest.TestCase):
 def bad(self,mutate):
  q=copy.deepcopy(adapter);mutate(q)
  with self.assertRaises((AssertionError,KeyError,ValueError)):a.adapter_audit(q,receipt,corpus)
 def row_mutate(self,q,key,value):
  rows=[a.json.loads(l) for l in q['runs'][0]['jsonl'].splitlines()];rows[1][key]=value;text='\n'.join(a.json.dumps(r,ensure_ascii=False) for r in rows)+'\n';q['runs'][0].update(jsonl=text,sha256=a.sha(text.encode()))
 def test_original(self):self.assertEqual(a.adapter_audit(adapter,receipt,corpus)['actual_original_annotated_rows'],66570)
 def test_missing_partition(self):self.bad(lambda q:q['runs'].pop())
 def test_false_gold_group(self):self.bad(lambda q:self.row_mutate(q,'expected',['invented']))
 def test_false_gold_match(self):self.bad(lambda q:self.row_mutate(q,'matched',not a.json.loads(q['runs'][0]['jsonl'].splitlines()[1])['matched']))
 def test_changed_candidate_count(self):self.bad(lambda q:q['runs'][0]['summary'].update(mean_candidates=0))
 def test_contextual_promotion(self):self.bad(lambda q:q.update(contextual_verdict='correct'))
if __name__=='__main__':unittest.main()
