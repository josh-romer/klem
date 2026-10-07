"""Reject omitted source targets, broad boundaries and fabricated captured paths."""
import copy,gzip,json,unittest
from pathlib import Path
from unittest.mock import patch
import double_past_prefinal_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source,cls.owners,cls.draft,cls.suite=map(audit.read,['source','owners','draft','suite'])
  cls.browser=json.loads(gzip.decompress((audit.ROOT/'docs/double-past-prefinal-main-browser.json.gz').read_bytes()))
 def targets(self,draft=None,suite=None):audit.verify_targets(self.source,draft or self.draft,suite or self.suite)
 def test_portable_audit_never_opens_original_runtime_or_exports(self):
  original=Path.read_bytes
  forbidden=set(self.source['frozen_inputs'])
  forbidden.update(str(audit.ROOT/name) for name in self.owners['source_hashes'])
  def archived(path):
   self.assertNotIn(str(path),forbidden)
   return original(path)
  with patch.object(Path,'read_bytes',archived):
   self.assertEqual(audit.verify()['groups'],11)
 def test_original_dialogue_reply_cannot_disappear(self):
  d=copy.deepcopy(self.draft);d['cases']=[c for c in d['cases'] if c['surface']!='알아봤었는데']
  with self.assertRaises(AssertionError):self.targets(draft=d)
 def test_second_polite_decomposition_cannot_disappear(self):
  d=copy.deepcopy(self.draft);next(c for c in d['cases'] if c['surface']=='두었었는데요')['judgments'].pop()
  with self.assertRaises(AssertionError):self.targets(draft=d)
 def test_single_past_cannot_replace_double_past(self):
  d=copy.deepcopy(self.draft);d['cases'][0]['judgments'][0]['morphemes'].pop(0)
  with self.assertRaises(AssertionError):self.targets(draft=d)
 def test_boundary_cannot_be_broadened_to_whole_lemma(self):
  d=copy.deepcopy(self.draft);d['cases'][-1]['judgments'][0].pop('morphemes')
  with self.assertRaises((AssertionError,KeyError)):self.targets(draft=d)
 def test_implementation_cap_cannot_be_reported_as_source_prohibition(self):
  s=copy.deepcopy(self.suite);s['review_status']='Source-certified universal triple-past prohibition.'
  with self.assertRaises(AssertionError):self.targets(suite=s)
 def test_self_consistent_json_span_corruption_is_rejected(self):
  source=copy.deepcopy(self.source);r=source['runs'][0];frames=[json.loads(l) for l in r['jsonl'].splitlines()]
  frames[0]['span']['end']+=1;r['jsonl']=''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in frames);r['sha256']=audit.sha(r['jsonl'].encode())
  with self.assertRaises(AssertionError):audit.verify_streams(source,self.draft)
 def test_fabricated_named_forbidden_path_is_rejected(self):
  d=copy.deepcopy(self.draft);r=next(r for r in d['probes'] if r['case']=='double-past-prefinal-boundary-5');response=json.loads(r['json'])
  j=d['cases'][-1]['judgments'][0];a={'lemmas':[{'text':j['lemmas'][0],'kind':'predicate'}],'morphemes':[{'form':f,'kind':k} for f,k in zip(j['morphemes'],j['morpheme_kinds'],strict=True)],'rules':['prefinal.past'],'unchanged':False}
  response['analyses'].append(a);r['json']=json.dumps(response,ensure_ascii=False)+'\n';r['sha256']=audit.sha(r['json'].encode());r['observations'][0]['matching_paths']=[a]
  with self.assertRaises(AssertionError):audit.verify_streams(self.source,d)
 def test_structural_observation_cannot_claim_contextual_certification(self):
  source=copy.deepcopy(self.source);source['contextual_verdict']='correct'
  with self.assertRaises(AssertionError):audit.verify_sources(source,self.owners)
 def test_after_api_must_preserve_ordered_components(self):
  b=copy.deepcopy(self.browser);b['responses'][0]['response']['breakdowns'][0][0].reverse()
  with self.assertRaises(AssertionError):audit.verify_browser(b,self.owners,self.suite)
 def test_after_api_cannot_drop_double_past_alias(self):
  b=copy.deepcopy(self.browser);b['responses'][0]['response']['grammar']['-었었-'].pop()
  with self.assertRaises(AssertionError):audit.verify_browser(b,self.owners,self.suite)
 def test_after_native_cannot_drop_original_sense(self):
  b=copy.deepcopy(self.browser);b['native'][0]['response']['entry']['senses'].pop()
  with self.assertRaises(AssertionError):audit.verify_browser(b,self.owners,self.suite)
if __name__=='__main__':unittest.main()
